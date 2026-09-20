# -*- coding: utf-8 -*-
from __future__ import print_function

from pyrevit import forms, script

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
