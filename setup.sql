CREATE TABLE orders (
  id bigserial PRIMARY KEY,
  customer_id int NOT NULL,
  amount numeric(10,2) NOT NULL,
  status text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  payload text NOT NULL
);
INSERT INTO orders (customer_id, amount, status, payload)
SELECT (random()*100000)::int, (random()*500)::numeric(10,2),
       (ARRAY['new','paid','shipped','refunded'])[1+(random()*3)::int],
       md5(g::text) || md5((g*7)::text) || md5((g*13)::text)
FROM generate_series(1,8000000) g;
ANALYZE orders;
