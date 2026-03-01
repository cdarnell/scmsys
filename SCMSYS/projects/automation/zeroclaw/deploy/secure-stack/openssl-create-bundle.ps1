openssl pkcs12 -export `
  -out certs/client.pfx `
  -inkey certs/client.key `
  -in certs/client-fullchain.pem `
  -passout pass: