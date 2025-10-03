-- Fix playoff game type structure by separating semifinals from championship games
-- This script adds a new 'playoffs_semi' game type and properly categorizes all playoff games

-- First, let's identify which games need to be updated
-- The pattern is: the last game of playoffs_championship in each year is the actual championship
-- All other playoffs_championship games are semifinals

-- 2025: Fix semifinals (keep only the last game as championship)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2025
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2025-08-22-BOS-SLC', '2025-08-22-ATL-MIN');

-- 2024: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2024
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2024-08-23-MIN-DC', '2024-08-23-CAR-SEA');

-- 2023: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2023
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2023-08-25-MIN-SLC', '2023-08-24-ATX-NY');

-- 2022: Fix semifinal
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2022
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2022-08-26-CAR-NY', '2022-08-25-CHI-COL');

-- 2021: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2021
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2021-09-10-RAL-CHI', '2021-09-10-SD-NY');

-- 2019: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2019
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2019-08-10-DAL-SD', '2019-08-10-IND-NY');

-- 2018: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2018
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2018-08-11-LA-MAD', '2018-08-11-NY-DAL');

-- 2017: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2017
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2017-08-26-TOR-DAL', '2017-08-26-SF-MAD');

-- 2016: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2016
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2016-08-06-SEA-MAD', '2016-08-06-TOR-DAL');

-- 2015: Fix semifinal
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2015
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2015-08-08-RAL-MAD', '2015-08-08-TOR-SJ');

-- 2014: Fix semifinal
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2014
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2014-07-26-MAD-SJ', '2014-07-26-NY-TOR');

-- 2013: Fix semifinals
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2013
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2013-08-03-NY-TOR', '2013-08-03-MAD-CHI');

-- 2012: Fix semifinals (only had 3 teams in playoffs)
UPDATE games
SET game_type = 'playoffs_semi'
WHERE year = 2012
  AND game_type = 'playoffs_championship'
  AND game_id IN ('2012-07-28-CIN-IND', '2012-08-05-RI-PHI');

-- Verify the changes
SELECT year, game_type, COUNT(*) as count
FROM games
WHERE game_type LIKE 'playoffs_%'
GROUP BY year, game_type
ORDER BY year DESC, game_type;