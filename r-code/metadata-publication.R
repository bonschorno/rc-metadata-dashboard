library(httr2)
library(jsonlite)
library(tidyverse)

# read API key
api_key <- readLines("/Users/cwalder/Desktop/api-keys/api-key-eth-collection.txt")

# Metadata about Publication ----------------------------------------------

path_to_publication_metadata <- "https://api.library.ethz.ch/research-collection/v2/statistics/usagereports/search/object?uri=https://www.research-collection.ethz.ch/entities/publication/"

publication_uuid <- "9cc98b6a-9e90-4ebe-930d-190177a4a419"

complete_path_to_publication <- paste0(path_to_publication_metadata, publication_uuid, "&&apikey=", api_key)

# Create a request object
request_publication_metadata <- request(complete_path_to_publication)

# Perform the GET request
response_publication_metadata <- req_perform(request_publication_metadata)

raw_json_publication_metadata <- resp_body_raw(response_publication_metadata)
publication_metadata_df <- fromJSON(rawToChar(raw_json_publication_metadata))