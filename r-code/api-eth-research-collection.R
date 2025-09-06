library(httr2)
library(jsonlite)
library(tidyverse)

# read API key
api_key <- readLines("/Users/cwalder/Desktop/api-keys/api-key-eth-collection.txt")

group_identifier <- "09746"

max_items <- "150"

path <- "https://api.library.ethz.ch/research-collection/v2/discover/search/objects?query=leitzahlCode%3A"

# Metadata about group ----------------------------------------------------

complete_path <- paste0(path, group_identifier, "&&size=", max_items, "&&apikey=", api_key)

# Create a request object
req <- request(complete_path)

# Perform the GET request
resp <- req_perform(req)

raw_json <- resp_body_raw(resp)
group_metadata <- fromJSON(rawToChar(raw_json))

#write_json(x = group_metadata, path = "group_metadata.json")

publication_names <- group_metadata[["_embedded"]][["searchResult"]][["_embedded"]][["objects"]][["_embedded"]][["indexableObject"]][["name"]]
publication_id <- group_metadata[["_embedded"]][["searchResult"]][["_embedded"]][["objects"]][["_embedded"]][["indexableObject"]][["uuid"]]

relevant_metadata <- c("dc.identifier.doi", "dc.type", "dc.date.issued", "dc.rights.license")

metadata_list <- vector("list", length(publication_names))

for (i in 1:length(publication_names)) {
  
  for (meta_data_indicator in relevant_metadata) {
    
    output <- group_metadata[["_embedded"]][["searchResult"]][["_embedded"]][["objects"]][["_embedded"]][["indexableObject"]][["metadata"]][[meta_data_indicator]][[i]][["value"]]
    
    if (is.null(output)) {
      metadata_list[[i]][[meta_data_indicator]] <- NA
    } else {
      metadata_list[[i]][[meta_data_indicator]] <- output
    }
    
  }
  
}

metadata_df <- bind_rows(metadata_list)

ghe_publication_data <- data.frame(name = publication_names,
                                   uuid = publication_id) |> 
  bind_cols(metadata_df) |> 
  rename(doi = dc.identifier.doi,
         publication_type = dc.type,
         date_issued = dc.date.issued,
         license = dc.rights.license,
         ) |> 
  mutate(year = as.numeric(substr(date_issued, 1, 4)),
         license = ifelse(is.na(license), "No license", license),
         license_short = case_when(license == "Creative Commons Attribution 4.0 International" ~ "CC BY 4.0",
                                   license == "Creative Commons Attribution-NonCommercial 4.0 International" ~ "CC BY-NC 4.0",
                                   license == "In Copyright - Non-Commercial Use Permitted" ~ "Copyright",
                                   license == "Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International" ~ "CC BY-NC-ND 4.0",
                                   license == "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International" ~ "CC BY-NC-SA 4.0",
                                   TRUE ~ license),
         license_short_group = case_when(str_detect(license_short, pattern = "4.0") ~ "CC BY 4.0",
                                         TRUE ~ license_short)
         ) |>
  mutate(publication_type_group = case_when(publication_type %in% c("Student Paper", "Bachelor Thesis", "Master Thesis") ~ "Student Paper",
                                            publication_type %in% c("Dataset", "Data Collection") ~ "Dataset",
                                            publication_type %in% c("Journal Article", "Review Article", "Book Chapter") ~ "Scientific Article",
                                            TRUE ~ "Other publication"
                                            ),
         doi_dummy = ifelse(is.na(doi), "No DOI", "Has DOI")) |> 
  relocate(doi_dummy, .after = doi) |> 
  relocate(year, .after = date_issued) |> 
  relocate(publication_type_group, .after = publication_type) |> 
  filter(year > 2010) |> 
  select(-uuid)

write_csv(ghe_publication_data, "ghe-research-collection.csv")
openxlsx::write.xlsx(ghe_publication_data, "ghe_research-collection.xlsx")