
-- install audit schema
-- set up test tables with auditdb-example sql.

select audit.leave_table('ae_a');
select audit.leave_table('ae_b');
select audit.leave_table('ae_c');



truncate audit.events;
truncate ae_a CASCADE;
truncate ae_b;
truncate ae_c;

select audit.audit_table('ae_a');
select audit.audit_table('ae_b');
select audit.audit_table('ae_c');

TRUNCATE ae_c;  -- truncate empty tabel results in event entry with no rows

INSERT INTO ae_a(a_text, a_number, a_decimal) VALUES
  ('Lorem', 382, 223.93992    ),
  ('ipsum',  50, 621          ),
  ('dolor', 479, 934.924255611),
  ('sit'  , 722,  63.491      ),
  ('amet.', 173, 649.2900000  );

select * from ae_a;

INSERT INTO ae_b(a_text, a_date, a_time) VALUES
  ('dolor', '2013-08-08'::date, '12:15'::time),
  ('ipsum', '1945-01-02'::date, '09:57'::time),
  ('Lorem', '1984-06-17'::date, '09:34'::time),
  ('ipsum', '2008-08-05'::date, '11:37'::time),
  ('sit'  , '1944-07-16'::date, '02:11'::time),
  ('Lorem', '1966-05-13'::date, '09:19'::time),
  ('ipsum', '1986-10-24'::date, '04:42'::time),
  ('amet.', '1961-11-16'::date, '04:48'::time),
  ('sit'  , '1973-10-22'::date, '18:12'::time),
  ('ipsum', '1934-01-11'::date, '03:55'::time);

-- trunc
TRUNCATE ae_b;

INSERT INTO ae_b(a_text, a_date, a_time) VALUES
  ('dolor', '2013-08-08'::date, '12:15'::time),
  ('ipsum', '1945-01-02'::date, '09:57'::time),
  ('Lorem', '1984-06-17'::date, '09:34'::time),
  ('ipsum', '2008-08-05'::date, '11:37'::time),
  ('sit'  , '1944-07-16'::date, '02:11'::time),
  ('Lorem', '1966-05-13'::date, '09:19'::time),
  ('ipsum', '1986-10-24'::date, '04:42'::time),
  ('amet.', '1961-11-16'::date, '04:48'::time),
  ('sit'  , '1973-10-22'::date, '18:12'::time),
  ('ipsum', '1934-01-11'::date, '03:55'::time);


INSERT INTO ae_c(test_key, test_value) VALUES
  ('d0ccb29413dc0dda46a58cd68b601349', 'Lorem ipsum dolor sit amet,   '),
  ('306dba61ebc32ab098a9d4adc38a3a7d', 'consectetur adipiscing elit.  '),
  ('498de31b4b9fbe3bdb16247ce8859ef4', 'Sed et tempor erat.           '),
  ('92dcc301ec35ed74eaaf68978fc56b94', 'Nulla posuere urna magna,     '),
  ('e10245b88f65b19a1243aaea98e12441', 'et vestibulum leo interdum eu.'),
  ('d5e9a73ab35d7506510960eb37af563b', 'Pellentesque imperdiet.       '),
  ('d2b4d8a219a32e444b9fc0cce5c1685e', 'consectetur adipiscing elit.  '),
  ('d75b9066192929d86983fc46ccff0125', 'Sed et tempor erat.           '),
  ('614e8c8587e96a751d8b02dfcd602fe2', 'Nulla posuere urna magna,     '),
  ('83c409b15efa02e49774f83bc782d002', 'et vestibulum leo interdum eu.');


UPDATE ae_c
  SET test_key = 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
  WHERE test_key =  'd75b9066192929d86983fc46ccff0125';

DELETE FROM ae_c
  WHERE test_key =  '92dcc301ec35ed74eaaf68978fc56b94';

DELETE FROM ae_c;

select * from audit.events;

-- delete and update do not work without primary key

-- SELECT generate_series(1,10) AS id, random() AS descr;
-- SELECT generate_series(1,10) AS id, NOW() - '1 year'::INTERVAL * (RANDOM() * 100) AS descr;
-- SELECT generate_series(1,10) AS id, md5(random()::text) AS descr;
