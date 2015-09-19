from http.server import *
from string import Template
import json

# ViewerTemplate is the HTML page template that will be served. It should
# handle the actual rendering of the Nestview tree.
ViewerTemplate = Template("""
<!DOCTYPE html>
<html><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Nestview</title>
    <style>
        body {
            font-family: "Menlo", "Consolas", "DejaVu Sans Mono",
                "Droid Sans Mono", "Courier", monospace;
            font-size: 14px;
        }

        .hidden { display: none; }
        code { font-family: inherit; color: gray; }
        p { margin: 0; }
        div#footer { margin-top: 1em; font-size: 12px; color: #bbb; }
        a { color: inherit; text-decoration: underline; }

        div.block {
            margin: 0;
            padding-left: 1.6em;
        }

        div.nav {
            margin: 1px; margin-left: 0;
            padding: 2px;
            background-color: #ddd;
        }
        div.nav > a {
            color: black;
            text-decoration: none;
        }
        div.nav > a > span {
            color: white;
            background-color: black;
            margin-right: 0.5em;
            padding-left: 0.3em; padding-right: 0.3em;
        }
        div.nav > a:hover {
            background-color: black;
            color: white;
        }

        div.textnode {
            margin: 1px; margin-left: 0;
            padding: 2px;
            background-color: #eee;
            padding-left: 0.3em;
        }
    </style>
</head><body onload="init()">
<div id="nv-container"></div>
<div id="footer">
    <a href="javascript:expandAll()">expand all</a>
<script>

/* Contains the initial tree to be rendered. */
nv_initial_tree = ${json}

/* Renders a tree to a DOM container (the parent). */
function renderTree (parent, tree) {
    if (tree === null) {
        return;
    }
    if (typeof(tree) === "object") {
        var expandable = createExpandable(parent, tree.shift());
        tree.forEach(function(node) {
            renderTree(expandable, node);
        });
    } else if (typeof(tree) === "string") {
        createString(parent, tree);
    }
}

/* Creates an expandable node and returns a <div> we can throw things in. */
function createExpandable (parent, text) {
    var node = document.createElement("div");
    node.classList.add("node");

    var nav   = document.createElement("div");
    var nav_a = document.createElement("a");
    var nav_s = document.createElement("span");
    var nav_t = document.createTextNode(text);

    nav.classList.add("nav");
    nav.appendChild(nav_a);
    nav.onclick = onExpandableClick;
    
    nav_a.href = "javascript:;";
    nav_a.appendChild(nav_s);
    nav_a.appendChild(nav_t);

    nav_s.textContent = "+";
    
    node.appendChild(nav)

    var block = document.createElement("div");
    block.classList.add("block");
    block.classList.add("hidden");
    node.appendChild(block);

    parent.appendChild(node);
    return block;
}

/* Creates a string node. */
function createString (parent, text) {
    var node = document.createElement("div");
    node.classList.add("node");
    node.classList.add("textnode");
    node.textContent = text;
    parent.appendChild(node);
}

/* When clicking an expandable node, we want to basically toggle a class on its
   class=block element. */
function onExpandableClick (evt) {
    evt.preventDefault();
    // 'this' should always be the div.nav, according to my old comments
    var block = this.parentNode.querySelector(".block");
    var expander = this.querySelector("a > span");
    if (block.classList.contains("hidden")) {
        block.classList.remove("hidden");
        expander.textContent = "-";
    } else {
        block.classList.add("hidden");
        expander.textContent = "+";
    }
    // is this needed, if we're calling preventDefault?
    return false;
}

/* Expand all elements. */
function expandAll () {
    var blocks = document.querySelectorAll(".block");
    var spans  = document.querySelectorAll(".nav > a > span");
    for (var i = 0; i < blocks.length; i++)
        blocks[i].classList.remove("hidden");
    for (var i = 0; i < spans.length; i++)
        spans[i].textContent = "-";
}

/* Load the initial tree when the page loads. */
function init () {
    nv_initial_tree.forEach(function(node) {
        renderTree(document.getElementById("nv-container"), node);
    });
}

</script>
</body></html>
""")

# ViewerRender takes a Nestview list and substitutes it, as a JSON array, into
# ViewerTemplate.
def ViewerRender (initialJSON = None):
    return ViewerTemplate.substitute(json = initialJSON)

# ObjectToTree takes a Python object of any type and returns a Nestview list.
def ObjectToTree (obj, name = None):
    try:
        prefix = ""

        # put the type as a name if no name was provided
        # this is a bit ugly, but type(obj) returns "<class 't'>" when I just
        # want "t"
        if name == None:
            name = "<" + repr(type(obj)).split("'")[1] + ">"
        # if a name has been provided, it's probably a key
        else:
            prefix = repr(name) + " = "

        # test for things that we shouldn't recurse on
        if type(obj) in [str, bytes]:
            return prefix + repr(obj)

        # test for dict-like things
        if hasattr(obj, "items"):
            tree = [name]
            for key, val in obj.items():
                tree.append(ObjectToTree(val, key))
            return tree

        # test for list-like things
        if hasattr(obj, "__iter__"):
            tree = [name]
            for item in obj:
                tree.append(ObjectToTree(item))
            return tree

        # test for objects and other things that have a __dict__ method
        if hasattr(obj, "__dict__"):
            if len(obj.__dict__) > 0:
                return ObjectToTree(obj.__dict__, prefix + repr(obj))

        # just return repr() for everything else
        return prefix + repr(obj)
    except TypeError:
        pass
    except IOError:
        pass
    return None


# NestviewHandler is a simple HTTP request handler that calls ViewerRender.
class NestviewHandler (BaseHTTPRequestHandler):
    def do_GET (self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(
            ViewerRender(self.nv_data),
            "utf-8"))
        return

# Launch the Nestview server.
def Nestview (data, address = ("127.0.0.1", 8000)):
    if type(data) == list:
        data = ObjectToTree(data)
    else:
        data = [ObjectToTree(data)]
    class LocalHandler (NestviewHandler):
        nv_data = data
    httpd = HTTPServer(address, LocalHandler)
    httpd.serve_forever()