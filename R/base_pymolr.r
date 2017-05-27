#' Control PyMol from R.
#'
#' Pymolr makes all PyMol commands available from R, and provides tools to
#' manipulate on PyMol selections.
#'
#' Use the \code{\linkS4class{Pymol}} class to interact with Pymol and the
#' \code{\linkS4class{Selection}} class to create PyMol selections.
"_PACKAGE"

#' Base class for PyMol connections.
#'
#' This base class implements all PyMol commands, but directly returns the data
#' returned by PyMol. The derived class \code{\link{Pymol}} performs
#' post-processing on certain methods and is the recommended interface.
BasePymol <- setRefClass("BasePymol",
                         fields=list(pid="integer",
                                     executable="character",
                                     args="character",
                                     url="character"))

BasePymol$methods(
    initialize = function(executable=Sys.which("pymol"), show.gui=FALSE,
                          rpc.port=9123) {
      "Initialise a new Pymol class."
      rpc.server <- system.file("extdata", "pymol_xmlrpcserver.py",
                                package="pymolr")
      .self$executable <<- executable
      .self$args <<- c("-q",
                       if(!show.gui) "-c",
                       rpc.server,
                       if(show.gui) "--rpc-bg",
                       "--rpc-port", rpc.port)
      .self$url <<- paste0("http://localhost:", rpc.port, "/RPC2")
      .self$pid <<- sys::exec_background(.self$executable, .self$args)
    },
    finalize = function() {
      "Closes PyMol when this class is garbage collected."
      .self$quit()
    },
    .rpc = function(method, ...) {
      "Call a remote PyMol method."
      XMLRPC::xml.rpc(.self$url, method, ...)
    }
)
