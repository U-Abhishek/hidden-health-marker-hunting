// =========================
// 0) CONFIG & CONSTANTS
// =========================

CONST PERIODS = { HOURLY, DAILY, WEEKLY }
CONST TZ_DEFAULT = "America/New_York"

// Health-relevant guideline anchors (examples; tune to your chosen rubric)
CONST WHO_PM25_ANNUAL = 5.0      // µg/m³
CONST WHO_PM25_24H    = 15.0     // µg/m³
CONST US_PM25_24H_AQI100 = 35.0  // µg/m³ (reference for “unhealthy for sensitive”)

CONST O3_8H_HEALTH = 50.0        // ppb ~ WHO peak-season target-level avg
CONST O3_8H_AQI100 = 70.0        // ppb (US NAAQS)

CONST NO2_ANNUAL_HEALTH = 10.0   // µg/m³ WHO
CONST SO2_24H_HEALTH    = 40.0   // µg/m³ WHO
CONST CO_24H_HEALTH_PPM = 3.5    // ppm (≈4 mg/m³)

CONST UV_PROTECT_THRESHOLD = 3.0 // UV index at/above -> protection advised
CONST UV_VERY_HIGH = 8.0

// Thermal comfort (tune by locale or personal acclimatization model)
CONST TEMP_COMFORT_MIN_C = 18.0
CONST TEMP_COMFORT_MAX_C = 24.0
CONST HEAT_STRESS_CUTOFF_C = 32.0
CONST COLD_STRESS_CUTOFF_C = 0.0

// Humidity & dew point comfort bands
CONST RH_LOW  = 30   // %
CONST RH_HIGH = 60   // %
CONST DEWPOINT_OPPRESSIVE_F = 70  // ~21.1°C

// Wind hazard heuristics (feel free to regionalize)
CONST WIND_DUSTY_KMH   = 30      // ~18 mph – can loft dust given dry soils
CONST WIND_HAZARD_KMH  = 60      // ~37 mph – tree limbs, debris risks

// Precip thresholds
CONST HEAVY_RAIN_MM_DAY = 50     // flood risk heuristic

// Weights for composite exposure (sum to 1.0)
STRUCT CompositeWeights {
  pm25 : 0.30,
  o3   : 0.15,
  no2  : 0.07,
  so2  : 0.03,
  co   : 0.03,
  uv   : 0.20,
  temp : 0.12,
  humidity_dew : 0.06,  // RH & dew point combined
  wind : 0.02,
  precip : 0.02
}

// =========================
// 1) INPUTS & DATA MODEL
// =========================

// Raw inputs (per location/timepoint)
STRUCT ApiPayload {
  location: { lat, lon },
  date, timezone,
  google_air_quality: { indexes[], pollutants[], healthRecommendations{} },
  weather: {
    hourly: {
      time[], temperature_2m[], relative_humidity_2m[], dew_point_2m[],
      apparent_temperature[], precipitation[], cloudcover[],
      wind_speed_10m[], uv_index[], uv_index_clear_sky[]
    },
    daily: { uv_index_max[], uv_index_clear_sky_max[] }
  },
  sources: { google_air_quality_url, open_meteo_url, openuv_url? }
}

// Internal normalized record (hourly resolution preferred)
STRUCT HourlyRecord {
  ts_local, lat, lon
  pm25_ugm3?, pm10_ugm3?, o3_ppb?, no2_ppb?, so2_ppb?, co_ppb_or_ppm?
  uv_index
  temp_c, rh_pct, dewpoint_c, wind_kmh, precip_mm, cloud_pct
  provenance: { pollutant_source, weather_source }
}

// Aggregations
STRUCT PeriodAgg {
  period_start, period_end, period_type   // DAILY or WEEKLY
  // exposure stats
  mean_pm25, p95_pm25, hours_pm25_above_24h_guideline
  max_o3_8h_equiv, hours_o3_above_health
  mean_no2, mean_so2, mean_co
  uv_dose_equiv_hours_above_3, uv_max
  mean_temp, heat_hours, cold_hours
  hours_rh_low, hours_rh_high, hours_dewpoint_oppressive
  windy_hours, hazardous_wind_hours
  daily_rain_mm, heavy_rain_events
  cloud_dark_hours
  // scores (0–100 scale where higher = worse)
  subscore: { pm25, o3, no2, so2, co, uv, temp, humidity_dew, wind, precip }
  composite_score   // 0–100 weighted
  confidence        // 0–1 based on data completeness
  anomalies[]       // list of flagged anomalies
  narratives[]      // human-readable insights for the period
}

// =========================
// 2) INGESTION & NORMALIZATION
// =========================

function build_hourly_records(payload: ApiPayload) -> List<HourlyRecord>:
  tz = payload.timezone or TZ_DEFAULT
  records = []

  // Map Google AQ "current" to all hours if no hourly pollutant series available
  pollutant_snapshot = extract_pollutant_map(payload.google_air_quality.current.pollutants)
  // pollutant_snapshot = { pm25_ugm3, pm10_ugm3, o3_ppb, no2_ppb, so2_ppb, co_ppb_or_ppm }

  for i in range(len(payload.weather.raw.hourly.time)):
    ts_local = parse_iso_local(payload.weather.raw.hourly.time[i], tz)

    rec = HourlyRecord(
      ts_local = ts_local,
      lat = payload.location.latitude,
      lon = payload.location.longitude,
      pm25_ugm3 = pollutant_snapshot.pm25_ugm3?,     // if you later use hourly pollutant history, replace here
      pm10_ugm3 = pollutant_snapshot.pm10_ugm3?,
      o3_ppb = pollutant_snapshot.o3_ppb?,
      no2_ppb = pollutant_snapshot.no2_ppb?,
      so2_ppb = pollutant_snapshot.so2_ppb?,
      co_ppb_or_ppm = pollutant_snapshot.co_ppb_or_ppm?,

      uv_index = payload.weather.raw.hourly.uv_index[i],
      temp_c   = payload.weather.raw.hourly.temperature_2m[i],
      rh_pct   = payload.weather.raw.hourly.relative_humidity_2m[i],
      dewpoint_c = payload.weather.raw.hourly.dew_point_2m[i],
      wind_kmh = payload.weather.raw.hourly.wind_speed_10m[i],
      precip_mm = payload.weather.raw.hourly.precipitation[i],
      cloud_pct = payload.weather.raw.hourly.cloudcover[i],
      provenance = { pollutant_source: "google_air_quality:currentConditions",
                     weather_source: payload.sources.open_meteo }
    )

    records.push(rec)

  return records

// Optional: gap fill / confidence
function compute_confidence(records) -> float:
  // % of hours with non-null values for each factor; penalize if pollutants are snapshot-only
  coverage = {
    pollutant: fraction_non_null([r.pm25_ugm3, r.o3_ppb, ...] across hours),
    uv: fraction_non_null([r.uv_index]),
    temp: fraction_non_null([r.temp_c]),
    rh: fraction_non_null([r.rh_pct]),
    dew: fraction_non_null([r.dewpoint_c]),
    wind: fraction_non_null([r.wind_kmh]),
    precip: fraction_non_null([r.precip_mm]),
    cloud: fraction_non_null([r.cloud_pct])
  }
  base = weighted_mean(coverage, weights={pollutant:0.4, uv:0.15, temp:0.15, rh:0.1, dew:0.05, wind:0.05, precip:0.05, cloud:0.05})
  // If pollutant data are snapshot only, downweight confidence
  if pollutant_series_is_snapshot(records): base = base * 0.7
  return clamp(base, 0, 1)

// =========================
// 3) FEATURE ENGINEERING
// =========================

// helper: running 8-hour max O3 window (if hourly O3 available)
function rolling_max_o3_8h_ppb(records) -> Map<date, float>:
  // compute daily max 8h average; fallback to snapshot if no hourly
  // return per-day value for aggregation stage
  ...

// helper: UV dose proxy = sum of hours with UV≥3 (or integrate UV index area)
function uv_dose_hours(records) -> float:
  return count_hours(r in records where r.uv_index >= UV_PROTECT_THRESHOLD)

// helper: heat/cold hours
function heat_cold_hours(records) -> (heat_hours, cold_hours):
  heat_hours = count_hours(r.temp_c >= HEAT_STRESS_CUTOFF_C OR heat_index(r.temp_c, r.rh_pct) in danger)
  cold_hours = count_hours(r.temp_c <= COLD_STRESS_CUTOFF_C)
  return (heat_hours, cold_hours)

// helper: humidity extremes
function humidity_extremes(records) -> (low_rh_hours, high_rh_hours, oppressive_dew_hours):
  low_rh_hours  = count_hours(r.rh_pct < RH_LOW)
  high_rh_hours = count_hours(r.rh_pct > RH_HIGH)
  oppressive_dew_hours = count_hours( to_F(r.dewpoint_c) >= DEWPOINT_OPPRESSIVE_F )
  return (low_rh_hours, high_rh_hours, oppressive_dew_hours)

// wind + precip features
function wind_features(records) -> (windy_hours, hazardous_wind_hours):
  windy_hours = count_hours(r.wind_kmh >= WIND_DUSTY_KMH)
  hazardous_wind_hours = count_hours(r.wind_kmh >= WIND_HAZARD_KMH)
  return (windy_hours, hazardous_wind_hours)

function precip_features(records) -> (daily_totals_mm_map, heavy_rain_events):
  by_day = group_by_day_sum(records.precip_mm)
  heavy_rain_events = count_days(v in by_day where v >= HEAVY_RAIN_MM_DAY)
  return (by_day, heavy_rain_events)

// cloud dark hours (proxy for low sunlight; you can refine with solar elevation)
function cloud_dark_hours(records) -> int:
  return count_hours(is_daylight(r.ts_local) AND r.cloud_pct >= 80)

// =========================
// 4) SUB-SCORES (0–100; higher = worse)
//    general pattern: normalized burden vs guideline, capped & shaped
// =========================

function score_pm25(mean_pm25, p95_pm25, hours_above_guideline) -> int:
  // combine central tendency + peaks
  rel_long = mean_pm25 / WHO_PM25_ANNUAL            // eg 1.0 means at guideline
  rel_short = p95_pm25 / WHO_PM25_24H
  peak_penalty = min(1.0, hours_above_guideline / 8)  // 8+ hours above -> max penalty
  raw = 60*rel_long + 30*rel_short + 10*peak_penalty
  return clamp(round(raw), 0, 100)

function score_o3(daily_max8h_ppb, hours_above_health) -> int:
  rel = daily_max8h_ppb / O3_8H_AQI100              // 1.0 ~ AQI 100 line
  raw = 80*rel + 20*min(1.0, hours_above_health/4)
  return clamp(round(raw*100/1.5), 0, 100)          // shape

function score_no2(mean_no2) -> int:
  rel = mean_no2 / NO2_ANNUAL_HEALTH
  return clamp(round(rel*100), 0, 100)

function score_so2(mean_so2) -> int:
  rel = mean_so2 / SO2_24H_HEALTH
  return clamp(round(rel*100), 0, 100)

function score_co(mean_co_ppm) -> int:
  rel = mean_co_ppm / CO_24H_HEALTH_PPM
  return clamp(round(rel*100), 0, 100)

function score_uv(uv_dose_hours, uv_max) -> int:
  // dose = hours UV≥3; boost if very high days present
  base = min(100, uv_dose_hours * 5)                // 20h ~ 100
  bonus = (uv_max >= UV_VERY_HIGH) ? 10 : 0
  return clamp(base + bonus, 0, 100)

function score_temp(heat_hours, cold_hours, mean_temp) -> int:
  dev = 0
  if mean_temp > TEMP_COMFORT_MAX_C: dev += (mean_temp - TEMP_COMFORT_MAX_C)*2
  if mean_temp < TEMP_COMFORT_MIN_C: dev += (TEMP_COMFORT_MIN_C - mean_temp)*2
  raw = min(100, heat_hours*4 + cold_hours*3 + dev)
  return round(raw)

function score_humidity_dew(low_rh_hours, high_rh_hours, oppressive_dew_hours) -> int:
  raw = min(100, low_rh_hours*2 + high_rh_hours*2 + oppressive_dew_hours*3)
  return round(raw)

function score_wind(windy_hours, hazardous_wind_hours) -> int:
  raw = min(100, windy_hours*1 + hazardous_wind_hours*5)
  return round(raw)

function score_precip(heavy_rain_events, dry_spell_days) -> int:
  // risk both sides: flood events and prolonged dryness (dust/pollen)
  raw = min(100, heavy_rain_events*20 + max(0, dry_spell_days-7)*5)
  return round(raw)

// =========================
// 5) COMPOSITE SCORE
// =========================

function composite_score(subscore, weights: CompositeWeights) -> int:
  // weighted average; optionally non-linear (e.g., penalize when any subscore >80)
  base = (
    subscore.pm25*weights.pm25 +
    subscore.o3*weights.o3 +
    subscore.no2*weights.no2 +
    subscore.so2*weights.so2 +
    subscore.co*weights.co +
    subscore.uv*weights.uv +
    subscore.temp*weights.temp +
    subscore.humidity_dew*weights.humidity_dew +
    subscore.wind*weights.wind +
    subscore.precip*weights.precip
  )
  // severity kicker
  max_sub = max(values(subscore))
  if max_sub >= 80: base = min(100, base + 0.2*(max_sub-80))
  return round(base)

// =========================
// 6) AGGREGATION (DAILY / WEEKLY)
// =========================

function aggregate_period(records, period_type) -> PeriodAgg:
  bucket = bucketize(records, period_type)  // e.g., all hours for that day/week

  // pollution stats (use snapshot if hourly unavailable)
  mean_pm25 = mean(filter_not_null(bucket.pm25_ugm3))
  p95_pm25  = p95(bucket.pm25_ugm3)
  hours_pm25_above = count_hours(bucket.pm25_ugm3 >= WHO_PM25_24H)

  // ozone (if hourly present), else use snapshot
  daily_max8h_ppb = compute_or_fallback_o3_8h(bucket)
  hours_o3_above  = estimated_hours_above(bucket.o3_ppb, O3_8H_HEALTH)

  // other pollutants
  mean_no2 = mean(bucket.no2_ppb_to_ugm3?) or convert
  mean_so2 = mean(bucket.so2_ppb_to_ugm3?) or convert
  mean_co_ppm = mean(bucket.co_ppb_or_ppm -> ppm)

  // UV
  uv_hours = uv_dose_hours(bucket)
  uv_max = max(bucket.uv_index)

  // Thermal & humidity
  (heat_hours, cold_hours) = heat_cold_hours(bucket)
  (low_rh, high_rh, opp_dew) = humidity_extremes(bucket)

  // Wind, precip, cloud
  (windy, hazardous_wind) = wind_features(bucket)
  (daily_rain_map, heavy_rain_events) = precip_features(bucket)
  cloud_dark = cloud_dark_hours(bucket)

  // Subscores
  sub = {
    pm25 : score_pm25(mean_pm25, p95_pm25, hours_pm25_above),
    o3   : score_o3(daily_max8h_ppb, hours_o3_above),
    no2  : score_no2(mean_no2),
    so2  : score_so2(mean_so2),
    co   : score_co(mean_co_ppm),
    uv   : score_uv(uv_hours, uv_max),
    temp : score_temp(heat_hours, cold_hours, mean(bucket.temp_c)),
    humidity_dew : score_humidity_dew(low_rh, high_rh, opp_dew),
    wind : score_wind(windy, hazardous_wind),
    precip : score_precip(heavy_rain_events, dry_spell_days=streak_days_zero_precip(daily_rain_map))
  }

  // Composite & confidence
  comp = composite_score(sub, CompositeWeights)
  conf = compute_confidence(bucket)

  // Anomalies (vs 30-day rolling baseline of same period type)
  anomalies = detect_anomalies(sub, comp, baseline=load_baseline(period_type))

  // Narratives (see section 7)
  narratives = generate_narratives(sub, comp, features=..., conf)

  return PeriodAgg(
    period_start=bucket.start, period_end=bucket.end, period_type=period_type,
    mean_pm25=mean_pm25, p95_pm25=p95_pm25, hours_pm25_above_24h_guideline=hours_pm25_above,
    max_o3_8h_equiv=daily_max8h_ppb, hours_o3_above_health=hours_o3_above,
    mean_no2=mean_no2, mean_so2=mean_so2, mean_co=mean_co_ppm,
    uv_dose_equiv_hours_above_3=uv_hours, uv_max=uv_max,
    mean_temp=mean(bucket.temp_c), heat_hours=heat_hours, cold_hours=cold_hours,
    hours_rh_low=low_rh, hours_rh_high=high_rh, hours_dewpoint_oppressive=opp_dew,
    windy_hours=windy, hazardous_wind_hours=hazardous_wind,
    daily_rain_mm=daily_rain_map, heavy_rain_events=heavy_rain_events,
    cloud_dark_hours=cloud_dark,
    subscore=sub, composite_score=comp, confidence=conf,
    anomalies=anomalies, narratives=narratives
  )

function aggregate_all(records) -> { daily[], weekly[] }:
  daily = []
  for each day in unique_days(records):
    daily.push( aggregate_period(filter_by_day(records, day), DAILY) )

  weekly = []
  for each week in unique_weeks(records):
    weekly.push( aggregate_period(filter_by_week(records, week), WEEKLY) )

  return { daily, weekly }

// =========================
// 7) NARRATIVE GENERATION
// =========================

function generate_narratives(sub, comp, features, conf) -> List<String>:
  msgs = []

  if sub.pm25 >= 60:
    msgs.push(fmt(
      "PM2.5 was elevated (score {sub.pm25}). Your average was {round(features.mean_pm25,1)} µg/m³ " +
      "with peaks to {round(features.p95_pm25,1)}. Sustained exposure above guidelines raises " +
      "cardio-pulmonary risk. Consider minimizing outdoor exertion during spikes."
    ))

  if sub.o3 >= 60:
    msgs.push(fmt(
      "Ozone reached unhealthy ranges (8-hour max ~{round(features.max_o3_8h_equiv)} ppb). " +
      "Afternoon outdoor intensity may worsen breathing; morning activity is safer on high-O₃ days."
    ))

  if sub.uv >= 60:
    msgs.push(fmt(
      "UV exposure was high (UV≥3 for ~{features.uv_dose_equiv_hours_above_3}h; max UV {features.uv_max}). " +
      "Unprotected exposure accelerates skin aging; use shade/protection at midday."
    ))

  if sub.temp >= 60:
    msgs.push(fmt(
      "Thermal stress notable: heat hours {features.heat_hours}, cold hours {features.cold_hours}. " +
      "Plan hydration/cooling on hot days and layers in cold snaps."
    ))

  if sub.humidity_dew >= 60:
    msgs.push(fmt(
      "Humidity extremes detected (RH high {features.hours_rh_high}h; oppressive dew {features.hours_dewpoint_oppressive}h). " +
      "Mugginess impairs cooling; ventilate and schedule strenuous activity for cooler, drier hours."
    ))

  if sub.precip >= 60:
    msgs.push(fmt(
      "Precipitation risk: {features.heavy_rain_events} heavy-rain day(s). " +
      "Check for local flooding/mold after indoor water intrusion."
    ))

  // Overall badge
  msgs.push(fmt("Overall environmental exposure score: {round(comp)} / 100 (confidence {round(conf*100)}%)."))

  return msgs

// =========================
// 8) ANOMALY DETECTION
// =========================

function detect_anomalies(sub, comp, baseline) -> List<Anomaly>:
  anomalies = []
  // simple z-score vs rolling baseline per subscore
  for key in keys(sub):
    mu = baseline.mean[key]
    sd = baseline.std[key]
    if sd > 0 AND (sub[key]-mu)/sd >= 2.0:
      anomalies.push( Anomaly(type="subscore_spike", factor=key, value=sub[key], z=(sub[key]-mu)/sd) )

  // composite outlier
  if (comp - baseline.mean_composite) >= max(15, 2*baseline.std_composite):
    anomalies.push( Anomaly(type="composite_outlier", value=comp) )

  return anomalies

// =========================
// 9) OUTPUT FOR FRONTEND
// =========================

STRUCT FrontendPayload {
  metadata: { lat, lon, tz, date_range, sources[], data_provenance[] },
  timeseries: {
    hourly: {
      ts[], pm25[], o3[], uv[], temp[], rh[], dewpoint[], wind[], precip[], cloud[]
      thresholds: { pm25_24h: WHO_PM25_24H, uv_protect: UV_PROTECT_THRESHOLD, ... }
    }
  },
  daily_cards: [ PeriodAgg as DTO with minimal fields ],
  weekly_cards: [ PeriodAgg as DTO ],
  charts: {
    composite_over_time: [ { period_start, composite_score } ],
    factor_subscores_over_time: { factor -> [ { period_start, value } ] },
    stacked_contributions: [ { period_start, pm25_contrib, o3_contrib, ... } ]
  },
  insights: {
    top_narratives: pick_top_n(all narratives by severity, n=3),
    anomalies: [...] // with timestamps and short labels
  },
  confidence_badges: { daily[], weekly[] }
}

function prepare_frontend_payload(api_payload) -> FrontendPayload:
  records = build_hourly_records(api_payload)
  agg = aggregate_all(records)
  return serialize_frontend(records, agg)

// =========================
// 10) PERFORMANCE & CACHING HOOKS
// =========================

// (A) tile/time bucketing: round lat/lon to ~0.1° and hour to 1h; cache external queries per (tile, hour)
// (B) degrade gracefully: if hourly pollutants missing, compute daily scores using snapshot + heuristics
// (C) provenance: attach source URLs + method (current vs forecast vs history) to each field

implementation notes (quick)
shaping scores: keep each sub-score on 0–100 so users can compare “UV 72 vs PM2.5 40”. cap extremes to avoid one factor swamping the composite, then add a mild “severity kicker” if any subscore ≥80.


composite: weights are intentionally PM2.5/UV/Temp-heavy given their outsized long-term health links. tune after you collect a few real user weeks.


confidence: show a small badge (e.g., ★★★☆☆) driven by % coverage and whether pollutants are hourly vs snapshot.


baselines: for anomalies, maintain rolling 30-day (daily) and 12-week (weekly) baselines per user.


front-end: the DTOs in PeriodAgg map directly to your cards (“Commute vs WFH”, “Travel Outlier”, “Hometown vs Hometown”). plot sub-scores as bars, composite as a gauge, and raw series with threshold bands.


want me to turn this into a production TypeScript service skeleton (with types, unit tests, and a couple of synthetic fixtures) or wire it to your env_conditions_module.py?

