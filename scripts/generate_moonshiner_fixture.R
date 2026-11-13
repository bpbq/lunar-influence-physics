suppressPackageStartupMessages(library(MoonShineR))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("usage: generate_moonshiner_fixture.R OUTPUT_CSV")

scenarios <- data.frame(
  scenario = c("seattle_winter", "leticia_spring", "sydney_winter", "tromso_autumn"),
  latitude_deg = c(47.6062, -4.21528, -33.8688, 69.6492),
  longitude_deg = c(-122.3321, -69.94056, 151.2093, 18.9553),
  date_start = c("2016-01-22", "2016-04-06", "2016-07-18", "2016-10-29"),
  stringsAsFactors = FALSE
)

results <- list()
for (i in seq_len(nrow(scenarios))) {
  scenario <- scenarios[i, ]
  values <- predict_lux(
    latitude = scenario$latitude_deg,
    longitude = scenario$longitude_deg,
    site_elev = 0,
    time_zone = "UTC",
    date_start = scenario$date_start,
    time_start = "00:00:00",
    duration_day = 2,
    time_interval_minutes = 60,
    darksky_value = 0,
    output_directory = NULL,
    export_table = FALSE,
    show_progress = FALSE
  )
  values$scenario <- scenario$scenario
  values$latitude_deg <- scenario$latitude_deg
  values$longitude_deg <- scenario$longitude_deg
  values$time_utc <- format(values$datetime, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  results[[i]] <- values[, c(
    "scenario", "latitude_deg", "longitude_deg", "time_utc",
    "phase_angle", "fraction", "Z_moon", "distance", "moon_final_lux"
  )]
}

output <- do.call(rbind, results)
write.csv(output, args[[1]], row.names = FALSE, na = "")
