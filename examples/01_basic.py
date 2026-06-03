"""Smoke-test: ping FreeCAD, create+save+close a scratch document."""

from freecad_rpc import FreeCADClient

fc = FreeCADClient()
assert fc.ping(), "FreeCAD MCP addon not reachable on localhost:9875"
print("ping OK")

# Open documents before we start
print("open docs:", fc.list_documents())

# Create scratch
res = fc.create_document("scratch_demo")
print("create:", res)

# Add a box
fc.create_object(
    "scratch_demo",
    {
        "Name": "Box1",
        "Type": "Part::Box",
        "Properties": {"Length": 100, "Width": 50, "Height": 25},
    },
)

# Save it
res = fc.save_document("scratch_demo", "/tmp/scratch_demo.FCStd")
print("save:", res)

# Close it
res = fc.close_document("scratch_demo")
print("close:", res)
