"""Build a movable assembly via App::Part + set_part_group recipe.

Reproduces the Bett_Klein pattern from the Demigny BIM model: a Part
container with several children at local coordinates, moved as a unit
by editing only Part.Placement.
"""

from freecad_rpc import FreeCADClient, recipes

fc = FreeCADClient()
fc.create_document("assembly_demo")

# Create the container
fc.create_object("assembly_demo", {"Name": "Assembly", "Type": "App::Part"})

# Children — each defined in the assembly's local coordinate system
for name, length, dx in [("Leg_FL", 50, 0), ("Leg_FR", 50, 200),
                         ("Leg_BL", 50, 0), ("Leg_BR", 50, 200)]:
    fc.create_object(
        "assembly_demo",
        {
            "Name": name,
            "Type": "Part::Box",
            "Properties": {
                "Length": length, "Width": length, "Height": 400,
                "Placement": {
                    "Base": {"x": dx, "y": 0 if "F" in name else 800, "z": 0},
                    "Rotation": {"Axis": {"x": 0, "y": 0, "z": 1}, "Angle": 0},
                },
            },
        },
    )

# Attach children to the Part — this is the step edit_object can't do
recipes.set_part_group(
    fc, "assembly_demo", "Assembly",
    ["Leg_FL", "Leg_FR", "Leg_BL", "Leg_BR"],
)

# Move the whole assembly by editing only the Part's Placement
fc.edit_object(
    "assembly_demo", "Assembly",
    {"Properties": {
        "Placement": {
            "Base": {"x": 5000, "y": 3000, "z": 0},
            "Rotation": {"Axis": {"x": 0, "y": 0, "z": 1}, "Angle": 45},
        }
    }},
)

print("Assembly moved as a unit. Check the GUI — all 4 legs should be at (5000,3000,0) rotated 45°.")
