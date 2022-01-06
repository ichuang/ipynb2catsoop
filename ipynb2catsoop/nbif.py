'''
Code for catsoop page which works in support of interfacing to a python notebook.
Instantiate this within a catsoop instance, at /nbif, using (within content.py):

    from ipynb2catsoop import nbif
    nbif.catsoop_response(globals())
'''
import json
import logging

class catsoop_response:
    '''
    Generate response from catsoop to a given HTTP query.
    The query should specify (via URL arguments or a POST):

        do = action to be taken, either "question" (default) or "auth"
        page = page to extract question from
        csq_name = name of question to be extracted from page
    '''
    def __init__(self, the_context):
        '''
        the_context = catsoop context, with cs_* variables defined
        '''
        self.the_context = the_context
        fields = ["cs_problem_spec", "cs_handler", "redirect_location", "cs_section_data",
                  "cs_url_root", "cs_path_info", "cs_username", "cs_form", "cs_course", 
                  "cs_user_info", "csm_user response", "content_type", "cs_additional_headers",
                  ]
        for field in fields:
            setattr(self, field, the_context.get(field))
        #the_context['cs_problem_spec'] = [f"hello2 {self.cs_username}"]
        #return

        #if (not self.cs_username) or (self.cs_username=="None"):
        #    self.cs_user_info = {}
        user_role = self.cs_user_info.get('role', None)
        is_staff = user_role in {'LA', 'TA', 'UTA', 'Admin', 'Instructor'}
        is_admin = user_role in {'Admin', 'Instructor'}
        is_student = user_role in {'Student'}

        do = self.cs_form.get("do", "question")
        page = self.cs_form.get("page")
        csq_name = self.cs_form.get("csq_name")

        if do=="auth":
            return self.do_auth()
        if page:
            return self.do_question_page(page, csq_name, doaction=do)

        self.the_context['cs_handler'] = "raw_response"
        self.the_context['content_type'] = "text/html"
        self.the_context['response'] = "unknown nbif action"
        
    def do_auth(self):
        '''
        Authentication page
        '''
        api_token = self.cs_user_info.get("api_token", "None")
        username = self.cs_user_info.get("username", "None")
        
        js = 'console.log("hello from iframe");'
        js += '''window.parent.postMessage({api_token: "%s", username: "%s"}, '*');''' % (api_token, username)
        js_chrome = """
            var nbauth_setup = function(){
                document.getElementById( 'cs_body' ).style['background-color'] = 'white';
                var felems = document.getElementsByTagName( 'footer' );
                Array.prototype.slice.call(felems).forEach(function(e){e.style.display='none'});
                if ( window.location == window.parent.location ){
                     console.log("not in iframe");
                     document.getElementById( 'nbif_msg' ).innerHTML = "Please go back to your python notebook now";
                }
            }
            if (document.readyState === "complete"){
                nbauth_setup();
            } else {
                document.addEventListener("DOMContentLoaded", nbauth_setup);
            }
        """
        js += js_chrome
        
        if self.cs_username=="None":
            url = f"{self.cs_url_root}/{self.cs_course}/nbif?do=auth&loginaction=login"
            html = f"please <a target='blank' href='{url}'>login</a>"
            html += f"<script type='text/javascript'>{js_chrome}</script></body>"
            self.the_context['cs_problem_spec'] = html
        else:
            html = f"You have been authenticated to catsoop as {self.cs_username}"
            html += "<div id='nbif_msg'></div>"
            html += f"<script type='text/javascript'>{js}</script></body>"
            self.the_context['cs_problem_spec'] = html
        return

    JS_iframe_resize = """
        console.log("hello nbif");
        var do_nbif_resize = function(){
            if ( window.self !== window.top ) {
        
        	var body = document.body,
        	    html = document.documentElement;
        	
        	var window_height = window.innerHeight;
        	window.originalInnerHeight = window_height;
        
        	var myheight = Math.max( body.scrollHeight, body.offsetHeight, 
        				 html.clientHeight, html.scrollHeight, html.offsetHeight );
        	myheight += 0;
        	var resize = function(){
        	    if (!window.parent.postMessage){
        		window.setTimeout(resize, 500);
        		console.log("[nbif_iframe_resize] no postMessage yet!");
        		return;
        	    }		
        	    console.log(`in iframe - doing resize, myheight=${myheight}, original height=${window.originalInnerHeight}`);
        	    try {
        		window.parent.postMessage(`{"subject":"lti.frameResize", "height":${myheight}}`, '*')
        	    }
        	    catch (err){
        		console.log(`Error doing resize: ${err}`);
        	    }
        	}
        	window.setTimeout(resize, 500);
            }
        };
        
        if (document.readyState === "complete" || (document.readyState !== "loading" && !document.documentElement.doScroll)) {
            do_nbif_resize();
        } else {
            document.addEventListener("DOMContentLoaded", do_nbif_resize);
        }

    """

    def do_question_page(self, page, csq_name, doaction=None):
        '''
        Display single question

        page = (str) name of catsoop page to load question from
        csq_name = (str) catsoop question name -- should be unique to each question on a given page
        doaction = (str) the <do> action requested in the HTTP GET urlargs or HTTP POST form
                   If doaction is "list" then return a list of available problems on the given page.
                   Otherwise return catsoop HTML for the specified question.
        '''
        from catsoop import loader, tutor, dispatch
        
        if type(page)==list:
            try:
                page = page[0]
                page = page.value
            except Exception as err:
                pass

        path = [self.cs_course, page]
        context = loader.generate_context(path)
        context["cs_course"] = self.cs_course
        context["cs_path_info"] = path
        context["cs_username"] = self.cs_username
        context["cs_user_info"] = self.cs_user_info
        context['csq_name'] = csq_name

        # load page into context
        cfile = dispatch.content_file_location(context, path)
        logging.error(f"[nbquestion] Loading course=%s, cfile=%s" % (self.cs_course, cfile) )
        loader.load_content(context, self.cs_course, path, context, cfile)

        # extract the problem spec with specified csq_name
        this_problem_spec = None
        problem_names = []
        for elt in context["cs_problem_spec"]:
            if isinstance(elt, str):  
                continue
            # each elt is (problem_context, problem_kwargs)
            m = elt[1]
            problem_names.append(m['csq_name'])
            if m['csq_name']==csq_name:
                this_problem_spec = elt

        if doaction=="debug":
            html = ""
            for elt in context["cs_problem_spec"]:
                if isinstance(elt, str):
                    html += f"<li><pre>{str(elt)[:100].replace('<','&lt;')}</pre><br/>"
                else:
                    html += f"<li><pre>{[ str(x)[:100].replace('<','&lt;') for x in elt]}</pre><br/>"
            self.the_context['response'] = html
            self.the_context['cs_handler'] = "raw_response"
            self.the_context['content_type'] = "text/html"
            return

        if doaction=="list":
            html = json.dumps({'problem_names': problem_names})
            self.the_context['response'] = html
            self.the_context['cs_handler'] = "raw_response"
            self.the_context['content_type'] = "application/json"
            return

        if not this_problem_spec:
            html = f"question with csq_name={csq_name} in page={page} not found"
        else:
            context['cs_problem_spec'] = [this_problem_spec]
            context['cs_form'] = {}
            context["cs_footer"] = ""
            context['cs_scripts'] += '<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/3.6.3/iframeResizer.contentWindow.min.js"></script>'
            context['cs_scripts'] += f'<script type="text/javascript">{self.JS_iframe_resize}</script>'
            context["cs_content_header"] = ''
            if (not self.cs_username) or (self.cs_username=="None"):
                 msg = 'Warning: you are not authenticated'
                 url = f"{self.cs_url_root}/{self.cs_course}/nbif?do=auth&loginaction=login"
                 msg += f"; please <a target='blank' href='{url}'>login</a> first."
                 msg += f"<br/>You may also need to enable third-party cookies for {self.cs_url_root}"
                 context["cs_content_header"] = msg
            try:
                cs_handle_lti_page_modifications(context)
            except Exception as err:
                pass
            res = tutor.handle_page(context)
            out = dispatch.display_page(context)  # tweak and display HTML
            html = out[2]
            html = html.replace('id="cs_header"', 'id="cs_header" style="display:none"')
            html = html.replace('id="cs_top_navigation"', 'id="cs_top_navigation" style="display:none"')
            html = html.replace('<footer>', '<footer style="display:none">')

        self.the_context['response'] = html
        self.the_context['cs_handler'] = "raw_response"
        self.the_context['content_type'] = "text/html"
        return
    
