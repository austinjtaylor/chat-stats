-- Migration: Fix playoff game type classification
-- Date: 2025-10-08
-- Purpose: Update game_type for all playoff games based on official playoff dates
-- Reference: docs/playoff_dates.txt

-- ==============================================================================
-- 2025 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2025-07-26)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2025
  AND DATE(start_timestamp) = '2025-07-26';

-- Division finals (2025-08-08, 2025-08-09)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2025
  AND DATE(start_timestamp) IN ('2025-08-08', '2025-08-09');

-- Semi finals (2025-08-22)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2025
  AND DATE(start_timestamp) = '2025-08-22';

-- Championship (2025-08-23)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2025
  AND DATE(start_timestamp) = '2025-08-23';

-- ==============================================================================
-- 2024 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2024-07-27, 2024-07-28)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2024
  AND DATE(start_timestamp) IN ('2024-07-27', '2024-07-28');

-- Division finals (2024-08-09, 2024-08-10)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2024
  AND DATE(start_timestamp) IN ('2024-08-09', '2024-08-10');

-- Semi finals (2024-08-24)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2024
  AND DATE(start_timestamp) = '2024-08-24'
  AND game_id IN ('2024-08-23-CAR-SEA', '2024-08-23-MIN-DC');

-- Championship (2024-08-24)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2024
  AND DATE(start_timestamp) = '2024-08-24'
  AND game_id = '2024-08-24-CAR-MIN';

-- ==============================================================================
-- 2023 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2023-07-29)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2023
  AND DATE(start_timestamp) = '2023-07-29';

-- Division finals (2023-08-11, 2023-08-12)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2023
  AND DATE(start_timestamp) IN ('2023-08-11', '2023-08-12');

-- Semi finals (2023-08-25)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2023
  AND DATE(start_timestamp) = '2023-08-25';

-- Championship (2023-08-26)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2023
  AND DATE(start_timestamp) = '2023-08-26';

-- ==============================================================================
-- 2022 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2022-08-13)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2022
  AND DATE(start_timestamp) = '2022-08-13';

-- Division finals (2022-08-20, 2022-08-21)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2022
  AND DATE(start_timestamp) IN ('2022-08-20', '2022-08-21');

-- Semi finals (2022-08-26)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2022
  AND DATE(start_timestamp) = '2022-08-26';

-- Championship (2022-08-27)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2022
  AND DATE(start_timestamp) = '2022-08-27';

-- ==============================================================================
-- 2021 SEASON PLAYOFFS
-- ==============================================================================

-- Division finals - Using specific game IDs to match exactly 4 games
-- 2021-08-28: DAL vs SD (note: home/away order in game_id)
-- 2021-08-29: MIN vs CHI
-- 2021-09-03: RAL vs DC
-- 2021-09-04: ATL vs NY
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2021
  AND game_id IN (
    '2021-08-28-DAL-SD',
    '2021-08-29-MIN-CHI',
    '2021-09-03-RAL-DC',
    '2021-09-04-ATL-NY'
  );

-- Semi finals (2021-09-10)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2021
  AND DATE(start_timestamp) = '2021-09-10';

-- Championship (2021-09-11)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2021
  AND DATE(start_timestamp) = '2021-09-11';

-- ==============================================================================
-- 2019 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2019-07-20)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2019
  AND DATE(start_timestamp) = '2019-07-20'
  AND game_id IN ('2019-07-20-DC-TOR', '2019-07-20-CHI-PIT');

-- Division finals (2019-07-20, 2019-07-21, 2019-07-27)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2019
  AND (
    (DATE(start_timestamp) = '2019-07-20' AND game_id = '2019-07-20-SD-LA')
    OR DATE(start_timestamp) IN ('2019-07-21', '2019-07-27')
  );

-- Semi finals (2019-08-10)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2019
  AND DATE(start_timestamp) = '2019-08-10';

-- Championship (2019-08-11)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2019
  AND DATE(start_timestamp) = '2019-08-11';

-- ==============================================================================
-- 2018 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2018-07-21, 2018-07-27)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2018
  AND (
    (DATE(start_timestamp) = '2018-07-27' AND game_id = '2018-07-27-RAL-AUS')
    OR (DATE(start_timestamp) = '2018-07-21' AND game_id IN ('2018-07-21-MIN-IND', '2018-07-21-DC-NY'))
  );

-- Division finals (2018-07-21, 2018-07-28)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2018
  AND (
    (DATE(start_timestamp) = '2018-07-21' AND game_id = '2018-07-21-SD-LA')
    OR DATE(start_timestamp) = '2018-07-28'
  );

-- Semi finals (2018-08-11)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2018
  AND DATE(start_timestamp) = '2018-08-11';

-- Championship (2018-08-12)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2018
  AND DATE(start_timestamp) = '2018-08-12';

-- ==============================================================================
-- 2017 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2017-07-29, 2017-08-04, 2017-08-11, 2017-08-12)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2017
  AND DATE(start_timestamp) IN ('2017-07-29', '2017-08-04')
  OR (
    year = 2017
    AND DATE(start_timestamp) = '2017-08-11'
    AND game_id = '2017-08-11-MTL-DC'
  )
  OR (
    year = 2017
    AND DATE(start_timestamp) = '2017-08-12'
    AND game_id = '2017-08-12-SJ-LA'
  );

-- Division finals (2017-08-12, 2017-08-13)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2017
  AND (
    (DATE(start_timestamp) = '2017-08-12' AND game_id IN ('2017-08-12-LA-SF', '2017-08-12-DC-TOR'))
    OR DATE(start_timestamp) = '2017-08-13'
  );

-- Semi finals (2017-08-26)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2017
  AND DATE(start_timestamp) = '2017-08-26';

-- Championship (2017-08-27)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2017
  AND DATE(start_timestamp) = '2017-08-27';

-- ==============================================================================
-- 2016 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2016-07-16, 2016-07-17)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2016
  AND (
    DATE(start_timestamp) = '2016-07-16'
    OR (DATE(start_timestamp) = '2016-07-17' AND game_id = '2016-07-17-ATL-RAL')
  );

-- Division finals (2016-07-17, 2016-07-23)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2016
  AND (
    (DATE(start_timestamp) = '2016-07-17' AND game_id = '2016-07-17-SEA-SF')
    OR DATE(start_timestamp) = '2016-07-23'
  );

-- Semi finals (2016-08-06)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2016
  AND DATE(start_timestamp) = '2016-08-06';

-- Championship (2016-08-07)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2016
  AND DATE(start_timestamp) = '2016-08-07';

-- ==============================================================================
-- 2015 SEASON PLAYOFFS
-- ==============================================================================

-- Round 1 (2015-07-24, 2015-07-25)
UPDATE games
SET game_type = 'playoffs_r1'
WHERE year = 2015
  AND (
    DATE(start_timestamp) = '2015-07-24'
    OR (DATE(start_timestamp) = '2015-07-25' AND game_id IN ('2015-07-25-PIT-CHI', '2015-07-25-SEA-SF'))
  );

-- Division finals (2015-07-25, 2015-07-26)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2015
  AND (
    (DATE(start_timestamp) = '2015-07-25' AND game_id IN ('2015-07-25-MAD-PIT', '2015-07-25-NY-TOR', '2015-07-25-RAL-JAX'))
    OR DATE(start_timestamp) = '2015-07-26'
  );

-- Semi finals (2015-08-08)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2015
  AND DATE(start_timestamp) = '2015-08-08';

-- Championship (2015-08-09)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2015
  AND DATE(start_timestamp) = '2015-08-09';

-- ==============================================================================
-- 2014 SEASON PLAYOFFS
-- ==============================================================================

-- Division finals (2014-07-18, 2014-07-19)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2014
  AND DATE(start_timestamp) IN ('2014-07-18', '2014-07-19');

-- Semi finals (2014-07-26)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2014
  AND DATE(start_timestamp) = '2014-07-26';

-- Championship (2014-07-27)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2014
  AND DATE(start_timestamp) = '2014-07-27';

-- ==============================================================================
-- 2013 SEASON PLAYOFFS
-- ==============================================================================

-- Division finals (2013-07-26, 2013-07-27)
UPDATE games
SET game_type = 'playoffs_div'
WHERE year = 2013
  AND DATE(start_timestamp) IN ('2013-07-26', '2013-07-27');

-- Semi finals (2013-08-03)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2013
  AND DATE(start_timestamp) = '2013-08-03';

-- Championship (2013-08-04)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2013
  AND DATE(start_timestamp) = '2013-08-04';

-- ==============================================================================
-- 2012 SEASON PLAYOFFS
-- ==============================================================================

-- Semi finals (2012-07-28, 2012-08-05)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2012
  AND DATE(start_timestamp) IN ('2012-07-28', '2012-08-05');

-- Championship (2012-08-11)
UPDATE games
SET game_type = 'playoffs_championship'
WHERE year = 2012
  AND DATE(start_timestamp) = '2012-08-11';

-- ==============================================================================
-- VERIFICATION QUERY
-- ==============================================================================
-- Run this to verify the migration worked correctly

SELECT
    year,
    game_type,
    COUNT(*) as game_count
FROM games
WHERE game_type != 'regular'
GROUP BY year, game_type
ORDER BY year DESC, game_type;
