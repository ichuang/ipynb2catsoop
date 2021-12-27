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
            iFrameResize({log:false, checkOrigin:false});
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
    def __init__(self, host=None, course=None, urlbase=None, do_register=True):
        '''
        Initialize catsoop interface
        host = (str) catsoop hostname
        course = (str) catsoop course number or name
        urlbase = (str) base URL of catsoop instance, including path to course 
                        (used if host & course not specified)
        do_register = (bool) register callback for js -- for google colab notebooks
        '''
        if host and course:
            urlbase = f"https://{host}/{course}"
        urlbase = urlbase or "https://localhost:6010/course"
        self.urlbase = urlbase
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
        url = f"{self.urlbase}/nbauth"
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
        url = f"{self.urlbase}/nbquestion?page={page}&csq_name={csq_name}"
        return IPython.display.HTML(f"""{self.JS_iframe_resize}
                    <iframe src='{url}' width='100%' height='50'></iframe>""")

