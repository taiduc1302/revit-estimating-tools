# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys

from pyrevit import forms, script

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
LIB = os.path.join(ROOT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.package import create_estimating_package

output = script.get_output()
output.close_others()
folder = forms.pick_folder(title="Select an exported estimating snapshot folder")
if not folder:
    script.exit()
try:
    package_path = create_estimating_package(folder)
except Exception as exc:
    forms.alert(str(exc), title="Estimating Package", warn_icon=True)
    script.exit()
output.print_md("# Estimating Package Created")
output.print_md("`%s`" % package_path)
output.print_md("\n> Package status remains `NOT_ESTIMATOR_VALIDATED` until independently reviewed.")
