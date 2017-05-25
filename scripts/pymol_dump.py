from __future__ import print_function
import inspect
import pymol.keywords
import re
import collections

R_HEADER = "#' @include pymolr.r"

R_METHOD_TEMPLATE = r"""
function({args}) {{
    '{docstring}'
    .self$.rpc({call_args})
}}""".lstrip()

R_TEMPLATE = r"""
BasePymol$methods(
{methods}
)
""".lstrip()

USAGE_TEMPLATE = r"""
\usage{{
pymol <- new("Pymol")
pymol${name}({args})
}}
""".lstrip()

DOCSTRING_TEMPLATE = r"""
{description}
See: \\code{{\\link{{{link}}}}}.
""".lstrip()

ARG_REGEXES = (
    re.compile("^(?P<arg>\w+)\s+=\s+(?:[^:]+):\s(?P<desc>.*)$", re.DOTALL),
    re.compile("^(?P<arg>\w+)\s+=\s+(?P<desc>\S.*)$", re.DOTALL),
    re.compile("^(?P<arg>\w+)\s+[<>]\s+\d:?\s+(?P<desc>\S.*)$", re.DOTALL),
)

Section = collections.namedtuple("Section", ["heading", "lines"])

def escape_quotes(string):
    return re.sub(r"(?<!\\)'", r"\\'", string)

def escape_braces(string):
    # Escape braces not preceded by a backslash.
    # This requires the addition of two backslashes because this is parsed
    # first by R and then by Rdoc, so "\\{" is escaped to "\{" by R, which
    # is escaped to "{" by Rdoc.
    return re.sub(r"(?<!\\)([{}])", r"\\\1", string)

def escape_args_rd(args):
    # Replace "..." with \dots{}
    escaped = []
    for arg in args:
        if arg == "...":
            arg = r"\dots"
        escaped.append(arg)
    return escaped

def strip_blank(lines):
    while len(lines) > 0 and not lines[0]:
        lines.pop(0)
    while len(lines) > 0 and not lines[-1]:
        lines.pop()
    return lines

def docstring_sections(docstring):
    sections = []
    lines = docstring.split("\n")
    for line in lines:
        # Skip leading empty lines
        if len(sections) == 0 and line == "":
            continue

        # If this is a section heading, start a new section
        heading_match = re.match(r"^[^ ].*$", line)
        if heading_match:
            sections.append(Section(heading_match.group(0), []))
        else:
            # Add unnamed section if we haven't encountered a header yet
            if len(sections) == 0:
                sections.append(Section(None, []))
            sections[-1].lines.append(escape_braces(line.lstrip()))

    # Convert list of selections to an ordered dict
    section_dict = collections.OrderedDict()
    for section in sections:
        section_dict[section.heading] = section.lines
    return section_dict

def docstring_to_rd(cmd_name, args_r, sections):
    out_rd = []
    out_rd.extend([
        r"\name{{{name}}}".format(name=cmd_name),
        r"\alias{{Pymol${name}}}".format(name=cmd_name),
        r"\title{{Execute PyMol '{name}' command}}".format(name=cmd_name),
    ])
    if "DESCRIPTION" in sections:
        out_rd.append(r"\description{")
        out_rd.extend(strip_blank(sections["DESCRIPTION"]))
        out_rd.append(r"}")
    else:
        out_rd.append(r"\description{Not described by PyMol.}")

    out_rd.append(USAGE_TEMPLATE.format(
        name=cmd_name,
        args=", ".join(escape_args_rd(args_r))
    ))

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
            out_rd.append(r"\note{")
            out_rd.extend(strip_blank(lines))
            out_rd.append(r"}")
        elif section == "ARGUMENTS":
            out_rd.append(r"\arguments{")
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

def build_r_body(cmd_name, cmd):
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
    args_r.extend(["{}={}".format(name, kwargs[name])
                   for name in argspec.args
                   if not name.startswith("_") and name in kwargs])
    # call_args_r: this is the arguments passed to xml.do
    # First, we add the method name. Call repr to add quotes
    call_args_r = [repr(cmd_name)]

    # This is the same list of arguments in the method signature, but
    # without the default values.
    call_args_r.extend([a for a in argspec.args if not a.startswith("_")])

    # Add a parameter for *args and **kwargs.
    if argspec.varargs is not None or argspec.keywords is not None:
        args_r.append('...')
        call_args_r.append("list(...)")

    #import pprint
    #pprint.pprint(docstring)

    return args_r, call_args_r


def dump_cmds():
    methods = []
    cmds = pymol.keywords.get_command_keywords()
    for cmd_name, cmd in cmds.iteritems():
        # Skip commands beginning with "_". I assume that they are internal.
        if cmd_name.startswith("_") or cmd[0] is pymol.cmd.python_help:
            continue

        # Get the list of args for the method and the args to be passed on.
        args_r, call_args_r = build_r_body(cmd_name, cmd)

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

    print(R_HEADER)
    print(R_TEMPLATE.format(methods=",\n".join(methods)))

if __name__ == "pymol":
    dump_cmds()
