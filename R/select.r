#' Class representing a Pymol selection.
#'
#' The following selectors are available. Short versions are given in
#' parentheses when available:
#'
#' \describe{
#' \item{symbol (e.)}{Character vector containing 1- or 2-letter chemical symbols.}
#' \item{name (n.)}{Character vector containing atom name codes.}
#' \item{resn (r.)}{Character vector of 3-letter amino acid codes or up to 2-letter codes for nucleic acids.}
#' \item{resi (i.)}{Integer vector of residue identifiers.}
#' \item{alt (NA)}{Character vector of single letter alternate conformation codes.}
#' \item{chain (c.)}{Character vector of single letter (sometimes number) chain identifiers.}
#' \item{segi (s.,)}{Character vector of segment identifiers.}
#' \item{flag (f.)}{Single integer from zero to 31.}
#' \item{numeric_type (nt.)}{Single integer.}
#' \item{text_type (tt.)}{Character vector of (up to) 4-letter codes.}
#' \item{id (NA)}{Integer vector of assigned atom  numbers.}
#' \item{index (idx.)}{Single integer}
#' \item{ss (NA)}{Character vector of single letter secondary structure codes.}
#' }

setClass("AbstractSelection")

pymol.properties = list(
  "symbol"="e.",
  "name"="n.",
  "resn"="r.",
  "resi"="i.",
  "alt"=NA,
  "chain"="c.",
  "segi"="s.,",
  "flag"="f.",
  "numeric_type"="nt.",
  "text_type"="tt.",
  "id"=NA,
  "index"="idx.",
  "ss"=NA
)

pymol.types = list(
  "symbol"="character",
  "name"="character",
  "resn"="character",
  "resi"="integer",
  "alt"="character",
  "chain"="character",
  "segi"="character",
  "flag"="integer",
  "numeric_type"="integer",
  "text_type"="character",
  "id"="integer",
  "index"="integer",
  "ss"="character"
)

Selection <- setClass("Selection",
                      contains=c("AbstractSelection"),
                      slots=c("selection"="list"))

setMethod("initialize",
          signature(.Object="Selection"),
          function(.Object, ...) {
  args <- list(...)
  pymol.args <- names(args) %in% names(pymol.properties)
  remaining.args <- args[!pymol.args]
  remaining.args$.Object <- .Object
  .Object <- do.call(callNextMethod, remaining.args)
  .Object@selection <- args[pymol.args]
  .Object
})

setMethod("|",
          signature(e1="AbstractSelection",
                    e2="AbstractSelection"),
          function(e1, e2) {
  new("BinaryBooleanSelection", children=c(e1, e2), operator="|")
})

setMethod("&",
          signature(e1="AbstractSelection",
                    e2="AbstractSelection"),
          function(e1, e2) {
  new("BinaryBooleanSelection", children=c(e1, e2), operator="&")
})

setMethod("!",
          signature(x="AbstractSelection"),
          function(x) {
  new("UnaryBooleanSelection", children=c(x), operator="!")
})

setMethod("as.character", signature(x="Selection"), function(x) {
  string.selectors <- mapply(function(attribute, value) {
    if(pymol.types[attribute] == "integer") {
      value <- squeeze.range(value)
    } else {
      # Escape empty strings
      value <- gsub('^$', '""', value)
      # Escape negative numbers
      value <- gsub("^-(\\d+)$", "\\-\1", value)
      # Join individual elements with "+" (or)
      value <- paste(value, collapse="+")
    }
    paste(attribute, paste(value, sep="+"), sep=" ")
  }, names(x@selection), x@selection)
  paste0(string.selectors, collapse=" & ")
})

squeeze.range <- function(sequence) {
    ranges <- integer(length(sequence))
    current_range <- 0
    for(i in seq_along(sequence)){
        if(i > 1){
            if(sequence[i] != sequence[i-1] + 1){
                current_range <- current_range + 1
            }
        }
        ranges[i] <- current_range
    }

    squeezed <- tapply(sequence, ranges, identity)
    squeezed <- lapply(squeezed, function(seq) {
      min <- min(seq)
      if(min < 0)
        min <- paste0("\\", min)
      if(length(seq) == 1)
        return(min)

      max <- max(seq)
      if(max < 0)
        max <- paste0("\\", max)
      paste(min, max, sep="-")
    })
    paste(squeezed, collapse="+")
}

BooleanSelection <- setClass("BooleanSelection",
                             contains="AbstractSelection",
                             slots=c("children"="list",
                                     "name"="character",
                                     "operator"="character"))

setMethod("initialize",
          signature(.Object="BooleanSelection"),
          function(.Object,
                   name=NA_character_,
                   operator,
                   children=NA,
                   ...) {
  .Object <- callNextMethod()
  .Object@children <- children
  .Object@operator <- operator
  .Object
})

BinaryBooleanSelection <- setClass("BinaryBooleanSelection",
                                   contains="BooleanSelection")
setMethod("initialize",
          signature(.Object="BinaryBooleanSelection"),
          function(.Object, ...) {
  .Object <- callNextMethod()
  .Object
})

UnaryBooleanSelection <- setClass("UnaryBooleanSelection",
                                  contains="BooleanSelection")
setMethod("initialize",
          signature(.Object="UnaryBooleanSelection"),
          function(.Object, ...) {
  .Object <- callNextMethod()
  .Object
})

setMethod("as.character", signature(x="BinaryBooleanSelection"), function(x) {
  paste0("(",
         vapply(x@children, as.character, ""),
         ")",
         collapse=paste0(" ", x@operator, " "))
})

setMethod("as.character", signature(x="UnaryBooleanSelection"), function(x) {
  paste0(x@operator, "(",
         vapply(x@children, as.character, ""),
         ")")
})

NamedSelection <- setClass("NamedSelection",
                           contains="AbstractSelection",
                           slots=c("name"="character"))
setMethod("initialize",
          signature(.Object="NamedSelection"),
          function(.Object, name, ...) {
  .Object <- callNextMethod(.Object, ...)
  .Object@name <- name
  .Object
})
setMethod("as.character", signature(x="NamedSelection"), function(x) {
  x@name
})
