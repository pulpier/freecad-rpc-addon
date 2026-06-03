"""Parametric model: bind geometry to a central VarSet via set_expression."""

from freecad_rpc import FreeCADClient, recipes

fc = FreeCADClient()
fc.create_document("param_demo")

# VarSet — single source of truth for dimensions
fc.create_object("param_demo", {"Name": "Vars", "Type": "App::VarSet"})

# Add a Length property to it
fc.execute_code(
    "import FreeCAD\n"
    "vs = FreeCAD.getDocument('param_demo').getObject('Vars')\n"
    "vs.addProperty('App::PropertyLength', 'box_len', 'Dims', 'Box length')\n"
    "vs.box_len = '200 mm'\n"
    "FreeCAD.getDocument('param_demo').recompute()\n"
)

# Create a Box and bind its Length to Vars.box_len
fc.create_object(
    "param_demo",
    {"Name": "MyBox", "Type": "Part::Box",
     "Properties": {"Width": 50, "Height": 50}},
)
recipes.set_expression(fc, "param_demo", "MyBox", "Length", "Vars.box_len")

print("Box.Length now follows Vars.box_len. Change box_len in the GUI, the box resizes.")
