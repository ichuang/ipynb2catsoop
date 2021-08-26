'''
Test pythoncode conversion and catsoop submission
'''
import catsoop
import unittest
from ipynb2catsoop import ipynb2catsoop

class Test_pythoncode(unittest.TestCase):
    def setUp(self):
        celltext_base = """#csq_pythoncode
#
# This is the code for the python code problem.  Each catsoop pythoncode problem 
# needs to specify at least four elements: 
#
# (1) The problem's name
# (2) The initial code shown to the student
# (3) The staff solution code
# (4) The tests performed to check the student's code, as a python list of dicts
#
# ipynb2catsoop can convert an ipython / jupyter notebook into a catsoop page,
# including python coding problems.  For the python coding problems, please
# include comments like '#csq_initial' (as shown in this example, below) to
# specify the four elements needed.  These comments should be at the start
# of the line, as single lines.
#
# An additional '#csq_submission' element can be included, to provide a sample
# student submission.  You can then see how this submission is graded, by 
# evaluating 'pythoncode_test(_i)' in a cell immediately after this cell is
# evaluated.

#csq_name
"exercise0"

#csq_initial
import numpy as np
def p(x):
    return # your code here

#csq_soln
import numpy as np
def p(x):
    return (1/(np.sqrt(2*np.pi*0.2)))*np.exp(-0.5*x**2.0/0.2)

#csq_tests
[{'code':'ans =[p(x) for x in range(10)]', 'check_function': pycode_equal}, ]
"""
        submission_ok = """
#csq_submission
import numpy as np
def p(x):
    return (1.0/(np.sqrt((1+1)*np.pi*0.2)))*np.exp(-0.5*x**2.0/0.2)
"""
        submission_bad = """
#csq_submission
import numpy as np
def p(x):
    return 3
"""
        self.celltext = celltext_base + submission_ok
        self.celltext_bad = celltext_base + submission_bad

    def test_code_parse1(self):
        I2C = ipynb2catsoop.ipynb2catsoop()
        parameters = I2C.celltext_to_parameters_pythoncode(self.celltext)
        for key in ['csq_soln', 'csq_name', 'csq_tests', 'csq_initial', 'csq_submission']:
            if not key in parameters:
                raise Exception(f"Missing {key} in parameters {parameters}")

    def test_code_catsoop1(self):
        '''
        Test creation of catsoop text from celltext input
        '''
        I2C = ipynb2catsoop.ipynb2catsoop()
        ret = I2C.make_pythoncode_problem(self.celltext, verbose=True)
        ctext = ret['text']
        print(ctext)
        assert type(ctext)==str
        assert '<question pythoncode>' in ctext
        assert """csq_sandbox_options = {'do_rlimits': False}""" in ctext

    def test_code_submit_csq_1(self):
        ipynb2catsoop.init_catsoop()
        ret = ipynb2catsoop.pythoncode_test(self.celltext, verbose=True, return_csq=True)
        assert 'csq' in ret

    def test_code_submit2(self):
        ipynb2catsoop.init_catsoop()
        ret = ipynb2catsoop.pythoncode_test(self.celltext, verbose=True, return_csq=False)
        print(ret)
        assert ret['score']==1

    def test_code_submit3(self):
        ipynb2catsoop.init_catsoop()
        ret = ipynb2catsoop.pythoncode_test(self.celltext_bad, verbose=True, return_csq=False)
        print(ret)
        assert ret['score']==0
