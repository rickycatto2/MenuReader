# Menu Reader

Photograph a restaurant menu or choose a photo or PDF. Menu Reader extracts dishes, sides, add-ons, and substitutions, then filters the results using preferences stored in your browser. Allergy messages flag possible concerns; always confirm ingredients and preparation with the restaurant.

## Run with Docker

1. Copy `.env.example` to `.env` and replace the placeholder with your OpenAI API key. Keep `.env` private.
2. Run `docker compose up -d --build` from this directory.
3. Visit `http://localhost:8000` and try a menu photo or PDF.

The container listens on port 8000, bound to the host's loopback address. If your existing Cloudflare Tunnel runs on this same host, point its service to `http://localhost:8000`. If it runs in another container, connect the containers on a shared Docker network and use `http://menu-reader:8000` instead.

Check status with `docker compose ps` and logs with `docker compose logs -f menu-reader`. Stop with `docker compose down`.

The app accepts one JPEG, PNG, WebP, GIF, or PDF menu file at a time, up to 20 MB. For PDFs, the API processes document text and page images; larger or longer menus may take more time and tokens. Preferences are saved in each browser's local storage, so no server data volume is needed.

