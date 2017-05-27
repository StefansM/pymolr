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
      .self$args <<- c("-q", "-Q",
                       if(!show.gui) "-c",
                       rpc.server,
                       if(show.gui) "--rpc-bg",
                       "--rpc-port", rpc.port)
      .self$url <<- paste0("http://localhost:", rpc.port, "/RPC2")

      # Before we start a pymol server, make sure that there is not one already
      # running on this port.
      if(tryCatch(.self$is.connected(), error=function(...) "err") != "err"){
        stop(paste("A process is already running on port", rpc.port))
      }

      .self$pid <<- sys::exec_background(.self$executable, .self$args)

      # Loop until the RPC server comes up. PyMol can take quite a long time to
      # start, so we might have to Sys.sleep() a few times until it comes up.
      exit.status <- NA
      max.tries <- 3
      connection.tries <- 0
      while(TRUE){
        exit.status <- sys::exec_status(.self$pid, wait=FALSE)
        if(!is.na(exit.status)
           || tryCatch(.self$is.connected(), error=function(cond) FALSE)
           || connection.tries == max.tries) {
          break
        }
        Sys.sleep(1)
        connection.tries <- connection.tries + 1
      }

      if(!is.na(exit.status)){
        stop(paste("Unable to start PyMol process. Exit status:", exit.status))
      }else if(connection.tries == max.tries){
        tools::pskill(.self$pid)
        stop("Couldn't connect to PyMol XMLRPC server.")
      }
    },
    finalize = function() {
      "Closes PyMol when this class is garbage collected."
      .self$quit()
    },
    is.connected = function() {
      "Check that the PyMol server is active."
      .self$.rpc("ping") == "pong"
    },
    .rpc = function(method, ...) {
      "Call a remote PyMol method."
      XMLRPC::xml.rpc(.self$url, method, ...)
    }
)
