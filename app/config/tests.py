from django.test import SimpleTestCase
from config import calc



class ClacTests(SimpleTestCase):

    def test_addènumbers(self):

        res = calc.add(5,6)

        self.assertEqual(res,11)
        
