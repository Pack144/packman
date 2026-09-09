-- Sync each Cub's Scouting America membership ID and expiration date,
-- generated from Pack144_Cub_Membership.csv.
--
-- This is one of two independent ways to apply the same update -- run this
-- file, or run update_cub_membership.py. They do not depend on each other;
-- pick whichever your admin tooling supports.
--
-- Each Cub is matched by an exact, case-sensitive First + Last name against
-- membership_member, since the CSV has no packman UUID/slug to match on.
-- (This differs from update_cub_membership.py, whose ORM match is
-- case-insensitive -- if a name here doesn't match a DB row's capitalization
-- exactly, that Cub's row here will silently affect zero rows.)
--
-- If a name matches zero rows in membership_member, its subquery returns
-- NULL and the UPDATE affects zero rows -- no error, in either engine. If a
-- name matches MORE than one row, behavior differs: SQLite silently uses one
-- of the matching rows, while PostgreSQL raises "more than one row returned
-- by a subquery used as an expression" and aborts the whole transaction (no
-- statements in this file are committed). Check row counts / errors after
-- running to confirm every statement matched exactly the Cub you expect.
--
-- Run with, e.g. (from the repo root):
--   sqlite3 db.sqlite3 < util/update_cub_membership.sql
--   psql "$DATABASE_URL" -f util/update_cub_membership.sql
--
-- Skipped at generation time (no MembershipID or ExpirationDate on file, 20 Cubs):
--   Desmond Allen
--   Andy Altamirano
--   Brooks Anderson
--   Llewyn Boyns
--   Carine Brunner
--   Salvatore Cangialosi
--   Solly Clarren
--   Nólie Estrada
--   Ben Graber
--   Asta Howell
--   Nick Hsieh
--   Dylan Jabbari
--   Chase Johnson
--   Malcolm Kastl
--   Easton Maddaloni
--   Malcolm Royalty
--   Cole Scheidtmann
--   Jacob Smith
--   Lily West
--   Liam Wu

BEGIN;

UPDATE membership_scout
SET scouting_membership_id = '141639279',
    scouting_membership_expires_on = '2027-07-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Wyatt' AND last_name = 'Adams'
);

UPDATE membership_scout
SET scouting_membership_id = '140959468',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Cory' AND last_name = 'Aderhold'
);

UPDATE membership_scout
SET scouting_membership_id = '140520740',
    scouting_membership_expires_on = '2026-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Milo' AND last_name = 'Almquist'
);

UPDATE membership_scout
SET scouting_membership_id = '140520762',
    scouting_membership_expires_on = '2026-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Nico' AND last_name = 'Altamirano'
);

UPDATE membership_scout
SET scouting_membership_id = '142472254',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'William' AND last_name = 'Appleyard'
);

UPDATE membership_scout
SET scouting_membership_id = '141035242',
    scouting_membership_expires_on = '2026-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Logan' AND last_name = 'Bernal'
);

UPDATE membership_scout
SET scouting_membership_id = '140704156',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Palmer' AND last_name = 'Bottorff'
);

UPDATE membership_scout
SET scouting_membership_id = '14870652',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Teddy' AND last_name = 'Busch'
);

UPDATE membership_scout
SET scouting_membership_id = '141675905',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Alexander' AND last_name = 'Cabral'
);

UPDATE membership_scout
SET scouting_membership_id = '140520516',
    scouting_membership_expires_on = '2026-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Carter' AND last_name = 'Campbell'
);

UPDATE membership_scout
SET scouting_membership_id = '142434582',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Jackson' AND last_name = 'Carter'
);

UPDATE membership_scout
SET scouting_membership_id = '140521039',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Parker' AND last_name = 'Champion'
);

UPDATE membership_scout
SET scouting_membership_id = '140959548',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Avery' AND last_name = 'Choate'
);

UPDATE membership_scout
SET scouting_membership_id = '141639268',
    scouting_membership_expires_on = '2027-07-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Peter' AND last_name = 'Clausen'
);

UPDATE membership_scout
SET scouting_membership_id = '14870885',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Will' AND last_name = 'Clausen'
);

UPDATE membership_scout
SET scouting_membership_id = '142416412',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Sloane' AND last_name = 'Collins'
);

UPDATE membership_scout
SET scouting_membership_id = '142443900',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Mason' AND last_name = 'Cousins'
);

UPDATE membership_scout
SET scouting_membership_id = '140520842',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Wren' AND last_name = 'Dangler'
);

UPDATE membership_scout
SET scouting_membership_id = '141628561',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Hugo' AND last_name = 'Deas'
);

UPDATE membership_scout
SET scouting_membership_id = '141050410',
    scouting_membership_expires_on = '2026-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Sammy' AND last_name = 'Dershowitz'
);

UPDATE membership_scout
SET scouting_membership_id = '14870670',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Velvel' AND last_name = 'Dershowitz'
);

UPDATE membership_scout
SET scouting_membership_id = '140964281',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Logan' AND last_name = 'Dubose'
);

UPDATE membership_scout
SET scouting_membership_id = '142418575',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Nat' AND last_name = 'Edson'
);

UPDATE membership_scout
SET scouting_membership_id = '141776023',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Oliver' AND last_name = 'Feiling'
);

UPDATE membership_scout
SET scouting_membership_id = '142405702',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Gage' AND last_name = 'Fenton-Close'
);

UPDATE membership_scout
SET scouting_membership_id = '142405720',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Calder' AND last_name = 'Fenton-Close'
);

UPDATE membership_scout
SET scouting_membership_id = '142435926',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Charlie' AND last_name = 'Fenwood Hughes'
);

UPDATE membership_scout
SET scouting_membership_id = '142439446',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Meir' AND last_name = 'Friedman'
);

UPDATE membership_scout
SET scouting_membership_id = '14870544',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Ryan' AND last_name = 'Gozzano'
);

UPDATE membership_scout
SET scouting_membership_id = '140376354',
    scouting_membership_expires_on = '2026-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Emily' AND last_name = 'Green'
);

UPDATE membership_scout
SET scouting_membership_id = '141629748',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'David' AND last_name = 'Hasten'
);

UPDATE membership_scout
SET scouting_membership_id = '141318922',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'William' AND last_name = 'Hegg'
);

UPDATE membership_scout
SET scouting_membership_id = '14870664',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Julia' AND last_name = 'Hirai-Hadley'
);

UPDATE membership_scout
SET scouting_membership_id = '142450651',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Adit' AND last_name = 'Holenarsipur'
);

UPDATE membership_scout
SET scouting_membership_id = '141107833',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Fran' AND last_name = 'Holman'
);

UPDATE membership_scout
SET scouting_membership_id = '141634252',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Leo' AND last_name = 'Hritz'
);

UPDATE membership_scout
SET scouting_membership_id = '141012044',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Nolan' AND last_name = 'Kelch'
);

UPDATE membership_scout
SET scouting_membership_id = '140521002',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Jude' AND last_name = 'Kelch'
);

UPDATE membership_scout
SET scouting_membership_id = '140520690',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Joe' AND last_name = 'Klatte'
);

UPDATE membership_scout
SET scouting_membership_id = '142434379',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Norbert' AND last_name = 'Kocar'
);

UPDATE membership_scout
SET scouting_membership_id = '142434386',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Oliver' AND last_name = 'Kocar'
);

UPDATE membership_scout
SET scouting_membership_id = '142434500',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'James' AND last_name = 'LaComb'
);

UPDATE membership_scout
SET scouting_membership_id = '14870861',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Leo' AND last_name = 'Markoff'
);

UPDATE membership_scout
SET scouting_membership_id = '141793246',
    scouting_membership_expires_on = '2026-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Celi' AND last_name = 'Maximo'
);

UPDATE membership_scout
SET scouting_membership_id = '141793292',
    scouting_membership_expires_on = '2026-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Bo' AND last_name = 'Maximo'
);

UPDATE membership_scout
SET scouting_membership_id = '142446154',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Caelan' AND last_name = 'McCracken'
);

UPDATE membership_scout
SET scouting_membership_id = '141832364',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Anders' AND last_name = 'McCracken'
);

UPDATE membership_scout
SET scouting_membership_id = '142383272',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Xavier' AND last_name = 'McVicar'
);

UPDATE membership_scout
SET scouting_membership_id = '140520966',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Quincy' AND last_name = 'McVicar'
);

UPDATE membership_scout
SET scouting_membership_id = '141623384',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Sam' AND last_name = 'Meguerditchian'
);

UPDATE membership_scout
SET scouting_membership_id = '142402735',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Jacob' AND last_name = 'Mondau'
);

UPDATE membership_scout
SET scouting_membership_id = '140521059',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Callum' AND last_name = 'Morse'
);

UPDATE membership_scout
SET scouting_membership_id = '141644185',
    scouting_membership_expires_on = '2027-07-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'William' AND last_name = 'Mosca'
);

UPDATE membership_scout
SET scouting_membership_id = '141629266',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Orion' AND last_name = 'Muller'
);

UPDATE membership_scout
SET scouting_membership_id = '140718816',
    scouting_membership_expires_on = '2026-11-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Dashiell' AND last_name = 'Nicodemus'
);

UPDATE membership_scout
SET scouting_membership_id = '140520641',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Garrison' AND last_name = 'Nielsen'
);

UPDATE membership_scout
SET scouting_membership_id = '141764175',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Fraser' AND last_name = 'Niffin'
);

UPDATE membership_scout
SET scouting_membership_id = '140520458',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Alex' AND last_name = 'Ostradicky'
);

UPDATE membership_scout
SET scouting_membership_id = '140520957',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Milo' AND last_name = 'Pahnke'
);

UPDATE membership_scout
SET scouting_membership_id = '14870877',
    scouting_membership_expires_on = '2026-12-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Vaso' AND last_name = 'Patterson'
);

UPDATE membership_scout
SET scouting_membership_id = '141635391',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Callan' AND last_name = 'Rooney'
);

UPDATE membership_scout
SET scouting_membership_id = '140967909',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Alexander' AND last_name = 'Royalty'
);

UPDATE membership_scout
SET scouting_membership_id = '142412560',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Linus' AND last_name = 'Russell'
);

UPDATE membership_scout
SET scouting_membership_id = '140520916',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Benjamin' AND last_name = 'Shendure'
);

UPDATE membership_scout
SET scouting_membership_id = '140960698',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Zuber' AND last_name = 'Stemen'
);

UPDATE membership_scout
SET scouting_membership_id = '142418028',
    scouting_membership_expires_on = '2027-08-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Akash' AND last_name = 'Sundar'
);

UPDATE membership_scout
SET scouting_membership_id = '141637695',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Bodhi' AND last_name = 'Thompson'
);

UPDATE membership_scout
SET scouting_membership_id = '141636711',
    scouting_membership_expires_on = '2027-05-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Johannes' AND last_name = 'Thoreen'
);

UPDATE membership_scout
SET scouting_membership_id = '141311240',
    scouting_membership_expires_on = '2027-10-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Olin' AND last_name = 'Tradal'
);

UPDATE membership_scout
SET scouting_membership_id = '141637015',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Clara' AND last_name = 'Walsworth'
);

UPDATE membership_scout
SET scouting_membership_id = '141031354',
    scouting_membership_expires_on = '2027-09-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Miles' AND last_name = 'Walsworth'
);

UPDATE membership_scout
SET scouting_membership_id = '140959383',
    scouting_membership_expires_on = '2027-06-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Walter' AND last_name = 'Weckner'
);

UPDATE membership_scout
SET scouting_membership_id = '141584633',
    scouting_membership_expires_on = '2027-07-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Samuel' AND last_name = 'Wise'
);

UPDATE membership_scout
SET scouting_membership_id = '141641731',
    scouting_membership_expires_on = '2026-07-31'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Ethan' AND last_name = 'Wu'
);

UPDATE membership_scout
SET scouting_membership_id = '140704138',
    scouting_membership_expires_on = '2026-11-30'
WHERE member_ptr_id = (
    SELECT uuid FROM membership_member WHERE first_name = 'Jude' AND last_name = 'Yukevich'
);

COMMIT;
