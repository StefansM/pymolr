#' Class containing a connection to a PyMol process.
#'
#' When this class is instantiated, a PyMol process is spawned. The PyMol
#' process may be manipulated using the methods in this class. When an instance
#' of this class is deleted (and garbage collected), the pymol process will be
#' closed.
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
#' @include base_pymolr.r
#' @include select.r
#' @export
Pymol <- setRefClass("Pymol", contains="BasePymol", methods=list(
  initialize = function(...) {
    callSuper(...)
  },
  load = function(...) {
    struc.name <- callSuper(...)
    NamedSelection(struc.name)
  },
  fetch = function(...) {
    struc.name <- callSuper(...)
    NamedSelection(struc.name)
  }
))

#' @importMethodsFrom XMLRPC rpc.serialize
setMethod("rpc.serialize", "AbstractSelection", function(x) {
  XML::newXMLNode("value",
                  XML::newXMLNode("string",
                                  XML::newXMLCDataNode(as.character(x))))
})
