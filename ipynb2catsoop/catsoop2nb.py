import os
import re
import IPython
from collections import defaultdict

class CatsoopInterface:
    '''
    Interface between python notebook and Catsoop instance.

    Instantiate this class to provide methods for authenticating user
    to catsoop instance, and displaying individual questions from a
    catsoop site within the python notebook.

    This allows a student to do learn material and do their work entirely
    from within a python notebook, and submit responses to questions from
    within the notebook.  The student should first authenticate to the
    catsoop instance, e.g. by running a notebook cell with code like:

      !pip3 install git+https://github.com/ichuang/ipynb2catsoop.git
      from ipynb2catsoop.catsoop2nb import CatsoopInterface
      CIF = CatsoopInterface(host="catsoop.univ.edu/cat-soop", course="1.01")
      CIF.do_auth()

    Confirmation that the authentication has succeeded can be obtained by
    running:

       CIF.print_auth()

    Then a specific catsoop question, from a given page
    (e.g. "test_problems"), and with a given name (e.g. "sum42"), can
    be instantiated, viewed, and interacted with, within the python
    notebook, using:

        CIF.show_question("test_problems", "sum42")

    The teacher should create questions on a catsoop instance, defining
    both the page where questions are located, and the name (csq_name)
    for each question.  Each page may have multiple questions, but
    each question must have a unique name.

    The catsoop instance should also have the nbif page installed.

    '''
    JS_iframe_resize = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/4.3.2/iframeResizer.min.js"
        integrity="sha512-dnvR4Aebv5bAtJxDunq3eE8puKAJrY9GBJYl9GC6lTOEC76s1dbDfJFcL9GyzpaDW4vlI/UjR8sKbc1j6Ynx6w=="
        crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <script type="text/javascript">
        var start_resize = function(){
            if (typeof(iFrameResize)=="undefined"){
                setTimeout(start_resize, 100);
                return;
            }
            iFrameResize({log:true, checkOrigin:false});
        }
        try { start_resize(); }
        catch(err){ console.log("[iframe_resize_for_catsoop] error: ", err); }
    </script>
    """

    JS_set_auth = """
    console.log("catsoop interface set_auth loaded")

    async function cs_set_auth(auth_token, username) {	// for colab notebooks
        const result = await google.colab.kernel.invokeFunction(
            'notebook.cif_set_auth', // The callback name.
            [auth_token, username], // The arguments.
            {}); // kwargs
    };

    window.addEventListener("message", (event) => {
        console.log(event);
        api_token = event.data.api_token;
        username = event.data.username;
        if (!api_token){
            console.log("[set_auth] ignoring message");
            return;
        }
        console.log(`api_token=${api_token}, username=${username}`);
        if (typeof IPython !== 'undefined'){
            console.log("setting catsoop auth info via IPython")
            IPython.notebook.kernel.execute(`CIF.set_auth("${api_token}", "${username}")`);
        }else{
            console.log("setting catsoop auth info via colab notebook interface")
            cs_set_auth(api_token, username)
        }
    });
    """    
    def __init__(self, host=None, course=None, urlbase=None):
        '''
        Initialize catsoop interface
        host = (str) catsoop hostname
        course = (str) catsoop course number or name
        urlbase = (str) base URL of catsoop instance, including path to course 
                        (used if host & course not specified)
        '''
        self.api_token = None
        self.username = None
        if host and course:
            urlbase = f"https://{host}/{course}"
        urlbase = urlbase or "https://localhost:6010/course"
        self.urlbase = urlbase
        do_register = "google.colab" in str(get_ipython())	# register callback for js in google colab notebooks
        if do_register:
            import google.colab 
            google.colab.output.register_callback('notebook.cif_set_auth', 
                                                  self.set_auth)
        return

    def set_auth(self, api_token, username):
        '''
        set catsoop authentication info (called by javascript)
        '''
        self.api_token = api_token
        self.username = username

    def do_auth(self):
        url = f"{self.urlbase}/nbif?do=auth"
        html = f'''<script type="text/javascript">{self.JS_set_auth}</script>
                   <iframe src="{url}" width=700 height=350></iframe>'''
        return IPython.display.HTML(html)   

    def print_auth(self):
        if self.api_token and self.username:
            print(f"You have been authenticated successfully as {self.username} to {self.urlbase}")
        else:
            print(f"Authentication not yet established to {self.urlbase}")

    def show_question(self, page="test_problems", csq_name="sum42"):
        '''
        Display specified (single) question in notebook output cell
        page = (str) catsoop page with questions
        csq_name = (str) name of question to display
        '''
        url = f"{self.urlbase}/nbif?page={page}&csq_name={csq_name}"
        return IPython.display.HTML(f"""{self.JS_iframe_resize}
                    <iframe src='{url}' width='100%' height='50'></iframe>""")

#-----------------------------------------------------------------------------

class catsoop2ipynb:
    '''
    Convert catsoop markdown page to ipython / jupyter notebook
    Questions are replaced with instantiations of links to the
    specified catsoop server, using calls to a CatsoopInterface
    instance.  Each question should have a csq_name specified,
    for this linking to work reliably.
    '''
    def __init__(self, page=None, hostname=None, course=None, ofn=None, verbose=False):
        '''
        page = name of catsoop page to convert (will read <page>/content.md)
        hostname = name of catsoop server (and port + path to catsoop instance, if needed) 
        course = course number/name used as part of the path within the catsoop instance
        ofn = output filename (defaults to <page>.ipynb)

        hostname and course need to be specified for linking to questions
        to work properly.
        '''
        self.page = page
        self.hostname = hostname
        self.verbose = verbose
        self.course = course
        self.ofn = ofn or f"{page}.ipynb"

    def make_question_link(self, csq_name):
        '''
        Return python code call to CIF to instantiate link to given named problem
        '''
        code  = f"# Evaluate this cell to show the interactive problem named {csq_name}\n"
        code += f'CIF.show_question("{self.page}", "{csq_name}")'
        return code

    def catsoop_interface_init_code(self):
        '''
        Return python code call to CIF which initializes authentication to catsoop server
        (this is where the catsoop instance's hostname & course are needed)
        '''
        code  =  "# Evaluate this and the following cell once, each time you start using the notebook\n"
        code +=  "# This code establishes an authenticated connection to the server used for interactive problems\n"
        code +=  "\n"
        code +=  "!pip3 install git+https://github.com/ichuang/ipynb2catsoop.git\n"
        code +=  "from ipynb2catsoop.catsoop2nb import CatsoopInterface"

        code2  =  "# Evaluate this cell to authenticate to the interactive problems server, after evaluating the cell above\n\n"
        code2 += f'CIF = CatsoopInterface(host="{self.hostname}", course="{self.course}")\n'
        code2 +=  'CIF.do_auth()'
        return code, code2

    def convert(self, catsoopfn=None):
        '''
        Generate <ofn> notebook file from <page>/content.md catsoop file
        '''
        import nbformat

        catsoopfn = catsoopfn or f"{self.page}/content.md"
        if not os.path.exists(catsoopfn):
            raise Exception(f"[catssop2nb] Oops!  Cannot find catsoop file {catsoopfn} -- aborting")

        if self.verbose:
            print(f"[catsoop2nb] Converting catsoop {catsoopfn} to '{self.ofn}'")

        with open(catsoopfn) as fp:
            catsoopmd = fp.read()
        
        nb = nbformat.v4.new_notebook()

        mode = None
        text = []
        qcode = None
        nb['cells'] = []
        unnamed_question_cnt = 0
        counts = defaultdict(int)

        def add_text_cell(text):
            if not text:
                return
            if all([x=="" for x in text]):
                return
            if counts['n_markdown_cells']==1:	# after first text cell, add CIF init code block
                code, code2 = self.catsoop_interface_init_code()
                nb['cells'].append(nbformat.v4.new_code_cell(code))
                nb['cells'].append(nbformat.v4.new_code_cell(code2))                
            cell = nbformat.v4.new_markdown_cell('\n'.join(text))
            nb['cells'].append(cell)
            counts['n_markdown_cells'] += 1

        for line in catsoopmd.split("\n"):
            if line.count("<question"):
                if text:
                    add_text_cell(text)
                    text = []
                qcode = [line]
                this_csq_name = None
                mode = "qcode"
                continue
            if mode=='qcode':
                qcode.append(line)
                if line.startswith("csq_name"):
                    env = {}
                    exec(line, env)
                    this_csq_name = env.get("csq_name")
                if line.count("</question"):
                    mode = None
                    if not this_csq_name:
                        this_csq_name = "q%06d" % unnamed_question_cnt
                        unnamed_question_cnt += 1
                    code = self.make_question_link(this_csq_name)
                    nb['cells'].append(nbformat.v4.new_code_cell(code))
                    counts['n_question_cells'] += 1
            else:
                pattab = {'section': '#',		# replace certain common catsoop XML with ipynb markdown
                          'subsection': '##',
                          'subsubsection': '###',
                          }
                skip = False
                for pat, mdstr in pattab.items():
                    m = re.match(f"<{pat}>([^<]+)</{pat}>", line)
                    if m:
                        add_text_cell(text)
                        add_text_cell([f"{mdstr} {m.group(1)}"])
                        text = []
                        skip = True
                        break
                if not skip:
                    text.append(line)
            
        if text:
            add_text_cell(text)

        with open(self.ofn, 'w') as ofp:
            nbformat.write(nb, ofp)
            if self.verbose:
                print(f"Wrote python notebook file {self.ofn}")
                print(f"    {counts['n_markdown_cells']} markdown cells and {counts['n_question_cells']} questions")
                print(f"    catsoop server host={self.hostname}, course={self.course}, page={self.page}")

#-----------------------------------------------------------------------------
# when run from command line

def C2I_CommandLine():

    import argparse
    help_text = """usage: %prog [args...] pagedir"""
    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("pagedir", help="input catsoop page directory (that has content.md)")
    parser.add_argument('-v', "--verbose", help="verbose output", action="store_true")
    parser.add_argument("--host", type=str, help="hostname of catsoop server (for question links)",
                        default="localhost:6010")
    parser.add_argument("-c", "--course", type=str, help="course number on catsoop server", default="1.01")
    parser.add_argument("-o", "--output-filename", type=str, help="name of output file (defaults to <pagedir>.ipynb if unspecified)", default=None)

    args = parser.parse_args()
    c2i = catsoop2ipynb(args.pagedir, args.host, args.course, args.output_filename,
                        verbose=args.verbose)
    c2i.convert()

if __name__=="__main__":
    C2I_CommandLine()
