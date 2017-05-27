"""
This script should be run by pymol, and is responsible for generating the
methods in the BasePymol class. It also generates documentation from the PyMol
help text of each command. See the "developing" vignette for more details.

This script will print method definitions to standard output. This output
should go in its own file, and adds methods to the BasePymol class. We also
generate documentation for each method, which is written into "man/".
"""

from __future__ import print_function
import inspect
import pymol.keywords
import pymol.helping
import re
import collections


# Template used when writing an R method.
R_METHOD_TEMPLATE = r"""
function({args}) {{
    '{docstring}'
    .self$.rpc({call_args})
}}""".lstrip()

# Template wrapping each method definition.  We need to include base_pymolr.r
# because it contains the definition of the BasePymol class to which we are
# adding methods.
R_TEMPLATE = r"""
#' @include base_pymolr.r
BasePymol$methods(
{methods}
)
""".lstrip()

# Written to .rd files for each method as the usage section.
USAGE_TEMPLATE = r"""
\usage{{
pymol <- new("Pymol")
pymol${name}({args})
}}
""".lstrip()

# Similarly for \description
DESCRIPTION_TEMPLATE = r"""
\description{{
{description}
}}
""".lstrip()

# Similarly for \note
NOTE_TEMPLATE = r"""
\note{{
{note}
}}
""".lstrip()

# Docstring for methods in the BasePymol reference class. The description is
# extracted from the docstring of the corresponding pymol methods.
DOCSTRING_TEMPLATE = r"""
{description}
See: \\code{{\\link{{{link}}}}}.
""".lstrip()

# Pymol describes the arguments to each command as free-ish text. These regexes
# capture the most common conventions.
ARG_REGEXES = (
    # Matches arguments of the form "argument = type: description".
    # For example, the "load" command.
    re.compile(r"""
        ^(?P<arg>\w+)   # Argument name
        \s+=\s+         # Separating " = "
        (?P<type>\w+):  # Type name, terminated by a colon
        \s(?P<desc>.*)$ # Description to end of line
        """, re.DOTALL | re.VERBOSE),
    # Arguments without a type: "argument = description".
    # For example, the "fetch" command.
    re.compile(r"""
        ^(?P<arg>\w+)   # Argument name
        \s+=\s+         # Seperating " = "
        (?P<desc>\S.*)$ # Description starts with first non-whitespace char
        """, re.DOTALL | re.VERBOSE),

    # Some commands specify a value range: "argument < val: description".
    # For example, the "zoom" command.
    re.compile(r"""
        ^(?P<arg>\w+)   # Argument name
        \s+
        (?P<range>
            [<>]\s+     # Operator (">" or "<")
            \d+         # Value range
        )
        :?\s+           # Optionally followed by a colon
        (?P<desc>\S.*)$ # Description starts with non-whistespace char
        """, re.DOTALL | re.VERBOSE),
)

# We represent a selection as a heading and a list of lines.
Section = collections.namedtuple("Section", ["heading", "lines"])

# We need to mangle some words that are keywords in R but not python.
def escape_keywords(str):
    return re.sub(r"\bfunction\b", ".function", str)

# R doesn't have raw strings, so we will need to escape single quotes.
def escape_quotes(string):
    return re.sub(r"(?<!\\)'", r"\\'", string)

# When writing .rd files, we will need to escape braces.
def escape_braces(string):
    return re.sub(r"(?<!\\)([{}])", r"\\\1", string)

# Given a list of arguments to be documented in a .rd file, escape any keywords
def escape_args_rd(args):
    # Replace "..." with \dots
    escaped = []
    for arg in args:
        if arg == "...":
            arg = r"\dots"
        escaped.append(arg)
    return escaped

# Remove leading and trailing blank lines from an array of lines.
def strip_blank(lines):
    while len(lines) > 0 and not lines[0]:
        lines.pop(0)
    while len(lines) > 0 and not lines[-1]:
        lines.pop()
    return lines

# Parse a docstring into a list of sections.
#
# Section headers in pymol docstrings are all caps and start in the first
# column.  The section bodies are indented. This function returns an ordered
# dictionary of Sections (named tuples) indexed by section name. Text that
# appears before any header has a section name of None.
def docstring_sections(docstring):
    sections = []
    lines = docstring.split("\n")
    for line in lines:
        # Skip leading empty lines
        if len(sections) == 0 and line == "":
            continue

        # If this is a section heading, start a new section. Here, we check for
        # non-space chars in the first column.
        heading_match = re.match(r"^[^ ].*$", line)
        if heading_match:
            sections.append(Section(heading_match.group(0), []))
        else:
            # Add unnamed section if we haven't encountered a header yet
            if len(sections) == 0:
                sections.append(Section(None, []))
            # Append line to most recently-seen section
            sections[-1].lines.append(escape_braces(line.lstrip()))

    # Convert list of selections to an ordered dict
    section_dict = collections.OrderedDict()
    for section in sections:
        section_dict[section.heading] = section.lines
    return section_dict

# The short docstrings in the BasePymol methods aren't long enough to fully
# describe most PyMol commands, so we also write a separate file documenting
# the method fully. I write the .rd file directly because I think going via
# roxygen2 would just make life more complicated.
def docstring_to_rd(cmd_name, args_r, sections):
    # Build up a list of lines in the output
    out_rd = []
    out_rd.extend([
        r"\name{{{name}}}".format(name=cmd_name),
        # Allow lookup by "help('Pymol$name')"
        r"\alias{{Pymol${name}}}".format(name=cmd_name),
        r"\title{{Execute PyMol '{name}' command}}".format(name=cmd_name),
    ])
    # \description
    if "DESCRIPTION" in sections:
        desc = "\n".join(strip_blank(sections["DESCRIPTION"]))
        out_rd.append(DESCRIPTION_TEMPLATE.format(description=desc))
    else:
        out_rd.append(r"\description{Not described by PyMol.}")

    # \usage
    out_rd.append(USAGE_TEMPLATE.format(
        name=cmd_name,
        args=", ".join(escape_args_rd(args_r))
    ))

    # These have either already been seen or should not appear.
    ignored_sections = (
        re.compile("^DESCRIPTION"),
        re.compile("^USAGE"),
        re.compile("^PYMOL API"),
        re.compile("^EXAMPLE"),
    )
    for section, lines in sections.iteritems():
        if len(lines) == 0 or len(strip_blank(lines)) == 0:
            continue

        elif section == "NOTES":
            note = "\n".join(strip_blank(lines))
            out_rd.append(NOTE_TEMPLATE.format(note=note))
        elif section == "ARGUMENTS":
            out_rd.append(r"\arguments{")
            # Split into paragraphs by joining by newline and splitting on
            # pairs of newlines
            argument_lines = "\n".join(strip_blank(lines)).split("\n\n")
            for argument_spec in argument_lines:
                for regex in ARG_REGEXES:
                    arg_match = regex.match(argument_spec)
                    if arg_match is not None:
                        break

                if arg_match is None:
                    item = (r"\item{{Extra (from PyMol help text)}}{{"
                        r"{definition}"
                        r"}}").format(definition=argument_spec)
                else:
                    item = r"\item{{{arg}}}{{{definition}}}".format(
                        arg = arg_match.group("arg"),
                        definition = arg_match.group("desc"))

                out_rd.append(item)
            out_rd.append(r"}")
        elif section == "SEE ALSO":
            out_rd.append(r"\seealso{")
            out_rd.append(r"\itemize{")
            # Join lines and then split on comma to give the list of commands
            for arg in re.split(r",\s*", ", ".join(lines)):
                if arg == "":
                    continue
                out_rd.append(r"\item \code{{\link{{Pymol${cmd}}}}}".format(
                        cmd=arg
                    ))

            out_rd.append(r"}")
            out_rd.append(r"}")
        else:
            if section is None:
                section = "Introduction"
            if any(regex.match(section) for regex in ignored_sections):
                continue
            out_rd.append(r"\section{{{}}}{{".format(
                section.strip().title()))
            out_rd.extend(strip_blank(lines))
            out_rd.append(r"}")
    return "\n".join(out_rd)

# Convert a default argument value to a value that can be understood by R.
# We do the following conversions:
#
# Lists to vectors: [1,2,3] -> c(1,2,3)
# Dicts to lists: {"a": 1, "b":2} -> list(`a`=1, `b`=2)
# None -> NULL
#
# For every other value, we just use its repr().
def to_r(arg):
    if isinstance(arg, list) or isinstance(arg, tuple):
        formatted_args = [to_r(x) for x in arg]
        return "c({})".format(", ".join(formatted_args))
    elif isinstance(arg, dict):
        joined_args = ["`{}`={}".format(n, to_r(v))
                       for n, v in arg.iteritems()]
        return "list({})".format(", ".join(joined_args))
    elif arg is None:
        return "NULL"
    else:
        return repr(arg)

# Given a python command, build the argument lists required for R.

# We build two argument lists: args_r and call_args_r. args_r is the argument
# list to be used in the method definition. call_args_r are passed on to the
# RPC call made by the method.

# We discard any arguments that start with an underscore on the assumption that
# they are intended to be internal to pymol.

# The argument lists we build reflect the python arguments as well as possible.
# For example, the arguments of  "def foo(a, b=123, *args):" are converted to
# "a, b=123, ...".

def build_r_args(cmd_name, cmd):
    fn = cmd[0]
    argspec = inspect.getargspec(fn)
    # print inspect.getargspec(fn)

    # Collect all arguments with a default
    # Remove the _self parameter -- it's an internal thing for pymol
    kwargs = {}
    if argspec.defaults is not None:
        kwargs = {arg: to_r(val)
                  for arg, val in zip(
                      reversed(argspec.args),
                      reversed(argspec.defaults))
                  if not arg.startswith("_")}

    # args_r are the R function parameters: function(args_r)
    # Collect args without a default parameter. These will be used in the R
    # function definition
    args_r = [arg for arg in argspec.args
              if not arg.startswith("_") and arg not in kwargs]

    # append kwargs to function parameters in "R" format (name=val)
    args_r.extend(["{}={}".format(escape_keywords(name), kwargs[name])
                   for name in argspec.args
                   if not name.startswith("_") and name in kwargs])
    # call_args_r: this is the arguments passed to xml.do
    # First, we add the method name. Call repr to add quotes
    call_args_r = [repr(cmd_name)]

    # This is the same list of arguments in the method signature, but
    # without the default values.
    call_args_r.extend([escape_keywords(a)
                        for a in argspec.args
                        if not a.startswith("_")])

    # Add a parameter for *args and **kwargs.
    if argspec.varargs is not None or argspec.keywords is not None:
        args_r.append('...')
        call_args_r.append("list(...)")

    return args_r, call_args_r


def dump_cmds():
    methods = []
    # Common commands
    cmds = pymol.keywords.get_command_keywords()
    # Some commands are separate, but we don't want to add methods for those
    # that just return a help message:
    pymol_helping = vars(pymol.helping).values()
    for cmd_name, cmd in pymol.keywords.get_help_only_keywords().iteritems():
        if cmd[0] not in pymol_helping:
            cmds[cmd_name] = cmd

    for cmd_name, cmd in cmds.iteritems():
        # Skip commands beginning with "_". I assume that they are internal.
        # Some are just warnings about python keywordss.
        if cmd_name.startswith("_") or cmd[0] is pymol.cmd.python_help:
            continue

        # Get the list of args for the method and the args to be passed on.
        args_r, call_args_r = build_r_args(cmd_name, cmd)

        # Start with a default docstring and replace it with the DESCRIPTION
        # section of the python docstring if it exists.
        method_docstring = escape_quotes(
            "PyMol '{name}' method".format(name=cmd_name))
        doc_sections = None
        if cmd[0].__doc__ is not None:
            # If a docstring is available, parse it into sections and reformat
            # it as an Rd file.
            doc_sections = docstring_sections(cmd[0].__doc__)
            if "DESCRIPTION" in doc_sections:
                desc_str = escape_quotes("\n".join(
                    doc_sections["DESCRIPTION"]
                ).strip())
                link_dst = "Pymol${name}".format(name=cmd_name)
                method_docstring = DOCSTRING_TEMPLATE.format(
                    description=desc_str,
                    link=link_dst)

        # These are the arguments that are passed on to xml.do.
        fn_body = R_METHOD_TEMPLATE.format(
            docstring=method_docstring,
            args=", ".join(args_r),
            call_args=", ".join(call_args_r)
        )
        methods.append("{}={}".format(cmd_name, fn_body))

        # Create documentation file for method
        if doc_sections is not None:
            rdoc_file = "man/Pymol-method-{}.Rd".format(cmd_name)
            with open(rdoc_file, "w") as fh:
                fh.write(docstring_to_rd(cmd_name, args_r, doc_sections))

    print(R_TEMPLATE.format(methods=",\n".join(methods)))

if __name__ == "pymol":
    dump_cmds()
