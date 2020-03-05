import os
import sys
print(os.environ)
print(sys.path)
from module.example import DOC
print(DOC)
inp = input(">> ")
print("inp: ", inp)
