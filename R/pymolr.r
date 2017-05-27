#' Start and communicate with a PyMol process.
#'
#' When this class is instantiated, a PyMol process is spawned. The PyMol
#' process may be manipulated using the methods in this class. When an instance
#' of this class is deleted (and garbage collected), the pymol process will be
#' closed.
#'
#' All commands from the PyMol API (excluding a few internal methods) are
#' exposed by this class. The majority of methods do not return a useful value,
#' and have been generated programatically from the PyMol API. These are
#' documented in \code{\link{BasePymol-class}}, but are identical to the
#' corresponding PyMol commands.
#'
#' Some methods process their arguments in a way designed to ease the interface
#' between \R and PyMol. These methods are documented in this file.
#
#' @section Communication with PyMol:
#'
#' This class communicates with PyMol using XML-RPC, an XML-based protocol
#' for remote procedure calls. Rather than use the default PyMol XML-RPC server
#' (the \code{-R} command line option of PyMol), we use a custom server that is
#' started by adding an extra python file to the pymol command line.
#'
#' @field pid Process ID of the running PyMol process.
#' @field executable The PyMol executable that is running.
#' @field args Command line arguments passed to PyMol
#' @field url URL of the RPC server.
#' @include select.r pymol_methods.r
#' @export
Pymol <- setRefClass("Pymol", contains="BasePymol", methods=list(
  initialize = function(...) {
    callSuper(...)
  },
  load = function(...) {
    "Load a structure and return a \\code{\\link{NamedSelection}}."
    struc.name <- callSuper(...)
    NamedSelection(struc.name)
  },
  fetch = function(...) {
    "Fetch a structure and return a \\code{\\link{NamedSelection}}."
    struc.name <- callSuper(...)
    NamedSelection(struc.name)
  },
  get_names = function(...) {
    "Return a list of \\code{\\link{NamedSelection}}s."
    names <- callSuper(...)
    lapply(names, NamedSelection)
  }
))

#' @importMethodsFrom XMLRPC rpc.serialize
setMethod("rpc.serialize", "AbstractSelection", function(x) {
  XML::newXMLNode("value",
                  XML::newXMLNode("string",
                                  XML::newXMLCDataNode(as.character(x))))
})
