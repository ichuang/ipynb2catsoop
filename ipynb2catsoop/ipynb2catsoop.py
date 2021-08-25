'''
Python code / class to convert ipython / jupyter notebook to catsoop page
'''

import os
import re
import sys
import glob
import json
import base64
import logging

try:
    import nbformat
except Exception as err:
    pass

class ipynb2catsoop:
    '''
    Convert ipython / jupyter notebook to catsoop
    '''
    def __init__(self, unit_name=None, course_dir=None, verbose=False, force_conversion=False):
        self.unit_name = unit_name
        self.course_dir = os.path.abspath(course_dir)
        self.verbose = verbose
        self.force_conversion = force_conversion

    def convert_all(self, cdir):
        '''
        Convert all */*.ipynb files to */content.md 

        Does this only if there is a single *.ipynb file in the directory
        
        cdir = (str) course content directory path
        '''
        cdir = os.path.abspath(cdir)
        self.course_dir = cdir
        if self.verbose:
            print(f"[ipynb2catsoop] Converting all */*.ipynb files in {cdir}")
        for unit_name in sorted(glob.glob(f"{cdir}/*")):
            if not os.path.isdir(unit_name):
                continue
            self.convert_unit(unit_name)

    def convert_unit(self, unit_name):
        '''
        Convert *.npynb file(s) in the specified unit_name directory
        '''
        if os.path.exists(f"{unit_name}/.ipynb2catsoop.ignore"):
            return
        nbfiles = list(glob.glob(f"{unit_name}/*.ipynb"))
        to_convert = {}
        if len(nbfiles)==0:
            return
        elif len(nbfiles)==1:
            to_convert[nbfiles[0]] = f"{unit_name}/content.md"
        else:
            for nbfn in nbfiles:
                to_convert[nbfn] = nbfn.replace(".ipynb", ".md")
            
        for nbfn, ofn in to_convert.items():
            self.unit_name = os.path.basename(unit_name)
            if (not self.force_conversion) and  os.path.exists(ofn) and os.path.getmtime(nbfn) < os.path.getmtime(ofn):
                if self.verbose:
                    print(f"    Skipping '{nbfn}' -- '{ofn}' already up to date")
                continue
            self.convert(nbfn, ofn=ofn)

    def convert(self, nbfn, ofn=None):
        '''
        Convert notebook *.ipynb file to content.md, saved using the configured course content directory
        '''
        odir = f"{self.course_dir}/{self.unit_name}"
        self.static_dir = f"{odir}/__STATIC__"
        if not ofn:
            ofn = f"{odir}/content.md"

        if self.verbose:
            print(f"[ipynb2catsoop] Converting python notebook '{nbfn}' to '{ofn}'")

        with open(nbfn) as fp:
            nbdata = fp.read()
        
        notebook = nbformat.reads(nbdata, as_version=4)
        
        with open(ofn, 'w') as fp:
            for cnt, cell in enumerate(notebook.cells):
                if self.verbose:
                    print("    " + str(cell)[:100])
                ctype = cell['cell_type']
                cell_md = cell.get('metadata', {})
                if ctype=="markdown":
                    if cell_md.get("id")=="view-in-github":	# skip "Open in Colab" at top of notebooks
                        continue
                    mdout = self.fix_markdown(cell['source'])
                    fp.write(mdout + "\n\n")
                    continue
                elif ctype=='code':
                    source = cell['source']
                    outputs = cell['outputs']
                    if source.startswith("# run this once at startup"):
                        continue
                    if source.startswith("# catsoop-ignore"):
                        continue
                    if source.count("ret = pythoncode_test(_i)"):
                        continue
                    if source.startswith("#csq_pythoncode"):
                        csq = self.make_pythoncode_problem(source)
                        fp.write(csq['text'])
                        continue
                    fp.write(f"<pre>{source}</pre>\n\n")
                    for out in outputs:
                        if 0:
                            fp.write(str(out) + "\n")
                        elif out['output_type']=='execute_result':
                            continue
                        elif out['output_type']=='display_data':
                            data = out['data']
                            for datacnt, (ctype, b64dat) in enumerate(data.items()):
                                if ctype.startswith("text"):
                                    fp.write(f'<p>{b64dat}</p>\n\n')
                                elif ctype.startswith("image"):
                                    fext = ctype.split("/")[-1]
                                    dfn = f"{self.static_dir}/cell_{cnt+1}_display_data_{datacnt+1:02d}.{fext}"
                                    dfnb = os.path.basename(dfn)
                                    if not os.path.exists(self.static_dir):
                                        os.mkdir(self.static_dir)
                                    with open(dfn, 'wb') as imfp:
                                        imfp.write(base64.b64decode(b64dat))
                                    fp.write(f'<img src="CURRENT/{dfnb}" alt="{dfnb}"/>\n\n')
                                else:
                                    print(f"Warning: unknown content type {ctype} in cell number {cnt+1}: skipping")
                            
    def fix_markdown(self, md):
        '''
        Fix markdown to match what is needed for catsoop.
        Specifically. rewrite image source links
        '''
        mdout = re.sub("(<img [^>]+>)", self.fix_img_url, md)
        return mdout

    def fix_img_url(self, mo):
        '''
        Fix image URL, from using cwd to the catsoop static path, with CURRENT/
        '''
        html = mo.group(0)

        def fix_url(umo):
            url = umo.group(1)
            if url.startswith("/") or url.startswith("CURRENT/"):
                return f'src="{url}"'
            self.ensure_static_file_copied(url)
            return f'src="CURRENT/{url}"'
            
        fixed = re.sub("""src[ ]*=[ ]*["']([^'"]+)["']""", fix_url, html)
        return fixed
        
    def ensure_static_file_copied(self, fnb):
        '''
        Ensure {course_dir}/{unit_name}/{fnb} is sync'ed with {course_dir}/{unit_name}/__STATIC__/{fnb}
        '''
        sfn = f"{self.course_dir}/{self.unit_name}/{fnb}"
        ddir = f"{self.course_dir}/{self.unit_name}/__STATIC__"
        dfn = f"{ddir}/{fnb}"
        if not os.path.exists(ddir):
            os.mkdir(ddir)
        if not os.path.exists(dfn) or os.path.getmtime(sfn) > os.path.getmtime(dfn):
            cmd = f"cp '{sfn}' '{dfn}'"
            if self.verbose:
                print(f"        {cmd}")
            os.system(cmd)

    def make_pythoncode_problem(self, celltext, verbose=False):
        optional_keys = ["csq_" + x for x in ['prompt']]
        required_keys = ["csq_" + x for x in ['initial', 'soln', 'tests']]
        keys = optional_keys + required_keys
        mode = None
        parameters = { k: "" for k in keys }
        for line in celltext.split("\n"):		# grab parameters from cell text
            line_done = False
            for key in keys:
                if line.startswith('#' + key):
                    mode = key
                    line_done = True
                    break
            if line_done:
                continue
            if mode:
                parameters[mode] += line + '\n'
        if verbose:
            print(json.dumps(parameters, indent=4))
        for key in required_keys:
            if not parameters[key]:
                raise Exception(f"[pythoncode_test] aborting - {key} undefined!")
    
        catsoop_text = ['']
        catsoop_text.append("<question pythoncode>")
        parameters['csq_interface'] = 'ace'
        raw_keys = ['csq_tests']
        
        for key in keys:
            if key in raw_keys:
                catsoop_text.append(f"{key} = {parameters[key]}" )
            else:
                catsoop_text.append((f"{key} =") + '"""' + parameters[key] + '"""' )
        catsoop_text.append( "\n" )
        catsoop_text.append( "csq_sandbox_options = {'do_rlimits': False}\n" )
        catsoop_text.append( "</question>\n\n" )
        catsoop_text = '\n'.join(catsoop_text)
        return {'text': catsoop_text}

    @staticmethod
    def do_submit(csq_submission=None, csq_soln="", csq_tests=None, csq_code_pre="",
                  verbose=True, return_csq=False, **kwargs):
        '''
        Run catsoop python code checker on the pythoncode problem with the given parameters
    
        if return_csq is True, then returns dict with csq, form, and info; else returns grader output,
        which is a dict with score and msg.
    
        submission = (str) code submission - nominally from student
        csq_soln = (str) staff code with the solution
        csq_tests = list of dicts, specifying tests to be performed on the code
                    note that for each test, the answer variable (ans) must have a value which is
                    serializable, e.g. a list of numbers.  It cannot be a python object.  This
                    is because in production, the answer is obtained from running python in a sandbox,
                    with the connection being strings passed back and forth.
        csq_code_pre = (str) code pre-pended to submission (and solution?) before running
        verbose = (bool) if True, then print out final score (should be 1 if correct, or 0 if incorrect) and msg
        '''
        if verbose > 1:
            ipynb2catsoop.set_verbose_logging()
            
        if not csq_submission:
            raise Exception("[pycode_question.do_submit] aborting: csq_submission is undefined!")
        if not csq_soln:
            raise Exception("[pycode_question.do_submit] aborting: csq_soln is undefined!")
        if not csq_tests:
            raise Exception("[pycode_question.do_submit] aborting: csq_tests is undefined!")
    
        context = {}
        # os.environ['CATSOOP_CONFIG'] = f"{os.getcwd()}/catsoop_config.py"
        loader.load_global_data(context)
        context["csq_python_interpreter"] = "/usr/local/bin/python"
        qkw = dict(
            csq_npoints=1,
            csq_code_pre=csq_code_pre,
            csq_initial="",
            csq_soln=csq_soln,
            csq_tests=csq_tests,
           )
        (csq, info) = context["tutor"].question(context, "pythoncode", **qkw)
        
        csq_name = "test_question"
        info["csm_loader"] = context["csm_loader"]
        info["csm_process"] = context["csm_process"]
        info["csm_util"] = context["csm_util"]
        info["csq_name"] = csq_name
        info["cs_version"] = context["cs_version"]
        info["cs_upload_management"] = ""
        info["cs_fs_root"] = context["cs_fs_root"]
        info["cs_cross_image"] = 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Red_x.svg/240px-Red_x.svg.png'
        info["cs_check_image"] = 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/Checkmark_green.svg/277px-Checkmark_green.svg.png'
        info["cs_python_interpreter"] = sys.executable
        info["csq_python_interpreter"] = sys.executable
        info["csq_python_sandbox"] = "python"
        info['csq_sandbox_options'] = {'do_rlimits': False}
        
        form = {csq_name: csq_submission}
        if return_csq:
            return {'csq': csq,
                    'form': form,
                    'info': info,
                }
    
        ret = csq["handle_submission"](form, **info)
        if verbose:
            print("score=", ret['score'])
            # print("msg=", ret['msg'])
            display(HTML(ret['msg']))
        return ret
    
    @staticmethod
    def pythoncode_test(celltext, verbose=False, return_csq=False):
        '''
        Call this function with _i as the celltext argument, in a jupyter notebook cell,
        to test the catsoop pythoncode problem defined in the previous cell.
        
        The cell should be a code cell, and have the following comments, used to define the corresponding 
        named catsoop pythoncode problem parameters:
    
        #csq_initial
        #csq_soln
        #csq_tests
        #csq_submission
        '''
        keys = ["csq_" + x for x in ['initial', 'soln', 'tests', 'submission']]
        mode = None
        parameters = { k: "" for k in keys }
        for line in celltext.split("\n"):		# grab parameters from cell text
            line_done = False
            for key in keys:
                if line.startswith('#' + key):
                    mode = key
                    line_done = True
                    break
            if line_done:
                continue
            if mode:
                parameters[mode] += line + '\n'
        if verbose:
            print(json.dumps(parameters, indent=4))
        for key in keys:
            if not parameters[key]:
                raise Exception(f"[pythoncode_test] aborting - {key} undefined!")
        try:
            parameters['csq_tests'] = eval(parameters['csq_tests'])
        except Exception as err:
            raise Exception(f"[pythoncode_test] aborting - could not evaluate csq_tests, got err={err}")
        return ipynb2catsoop.do_submit(return_csq=return_csq, **parameters)

    @staticmethod
    def set_verbose_logging():
        '''
        Make logger very verbose
        '''
        LOGGER = logging.getLogger("cs")
        LOGGER.disabled = False
        if getattr(LOGGER, 'verbose_catsoop_logging'):
            return
        LOGGER.setLevel(logging.DEBUG)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)
        LOGGER.verbose_catsoop_logging = 1

#-----------------------------------------------------------------------------

def pycode_equal(submission, solution):
    '''
    procedure used to check for correctness of test, given results from submission and from solution
    Old catsoop convention is that submission and solution are strings
    New catsoop convention (circa 2019) is that they are dicts, with the result string as key "result"
    '''
    if isinstance(submission, dict):
        submission = submission.get("result")
    if isinstance(solution, dict):
        solution = solution.get("result")
    if 0:	# for debugging
        print("submission=%s, solution=%s" % (submission, solution))
    return submission == solution

#-----------------------------------------------------------------------------
# use in an ipython / jypyter notebook

def init_catsoop():
    ccfn = "/tmp/config.py"
    with open(ccfn, 'w') as ofp:
        ofp.write("cs_data_root='/tmp'\n")

    import os
    os.environ['CATSOOP_CONFIG'] = ccfn
    from catsoop import check as csm_check
    import catsoop.base_context as base_context
    import importlib
    # base_context.os.environ['CATSOOP_CONFIG'] = ccfn
    base_context.cs_data_root = "/tmp"
    base_context.loader.base_context.config_loc = ccfn
    import catsoop.loader as loader
    from IPython.display import display, HTML
    
    importlib.reload(loader)
    loader.base_context = base_context
    globals()['csm_check'] = csm_check
    globals()['base_context'] = base_context
    globals()['loader'] = loader
    globals()['display'] = display
    globals()['HTML'] = HTML

    LOGGER = logging.getLogger("cs")
    LOGGER.disabled = False
    LOGGER.setLevel(1)

    globals()['pythoncode_test'] = ipynb2catsoop.pythoncode_test            

#-----------------------------------------------------------------------------
# when run from command line

def I2C_CommandLine():

    import argparse
    help_text = """usage: %prog [args...] notebook.ipynb"""
    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("ifn", help="input ipython / jupyter notebook file")
    parser.add_argument('-v', "--verbose", help="verbose output", action="store_true")
    parser.add_argument("-u", "--unit-name", type=str, help="catsoop unit name (subdir where content.md is to be stored); if unspecified, use current working dir",
                        default=".")
    parser.add_argument("-d", "--directory", type=str, help="directory where course content is located", default=".")
    parser.add_argument("--convert-all", action="store_true", help="convert all <inputfn>/*.ipynb notebooks, using <inputfn> as the course content directory")
    parser.add_argument("--force", action="store_true", help="force conversion even if output is newer than input")

    args = parser.parse_args()
    i2c = ipynb2catsoop(args.unit_name, args.directory, verbose=args.verbose, force_conversion=args.force)

    if args.convert_all:
        i2c.convert_all(args.ifn)
    else:
        i2c.convert(args.ifn)

if __name__=="__main__":
    I2C_CommandLine()
