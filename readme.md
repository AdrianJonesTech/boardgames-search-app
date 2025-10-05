# Board Games Search App

A full-stack Django web application for discovering and filtering top-ranked board games from BoardGameGeek (BGG). Users can search the top 1000 ranked games using filters like player count, playtime, weight (complexity), rating, and game mechanics. Results are displayed in a responsive card layout with thumbnails and links to BGG.

This project showcases modern web development skills, from backend API integration and database management to dynamic frontend interactions without heavy JavaScript frameworks.

## Features
- **Local Data Ingestion**: Scrapes and caches the top 1000 BGG games (with details like ratings, mechanics) into a local database for fast, offline searches.
- **Advanced Filtering**: Real-time search with ranges for players, time, weight, and rating; multi-select mechanics via a custom dropdown.
- **Dynamic UI**: Live updates without page reloads using HTMX; Bootstrap for responsive design; custom JS for interactive badges.
- **Admin Interface**: Django admin for viewing/editing games and mechanics.
- **Error-Resilient**: Handles API quirks, rate limits, and frontend edge cases.

## Skills Demonstrated
This portfolio project highlights a range of full-stack and DevOps skills:

### Backend Development
- **Django Framework**: Built models (e.g., `Game` with M2M to `Mechanic`), views (ORM queries for filtering), forms (validation for ranges/multi-select), and URL routing.
- **Database Management**: Django ORM for migrations, querying (e.g., `filter(min_players__gte=...)`), and relationships; ingested ~1000 records with batch API calls.
- **API Integration & Scraping**: Used `requests` and `BeautifulSoup` to scrape BGG rankings; parsed XML API (`xml.etree.ElementTree`) for game details/mechanics; implemented rate limiting (`time.sleep`).
- **Management Commands**: Custom Django commands (`fetch_top_games`, `fetch_mechanics`) for one-time data population.

### Frontend Development
- **Responsive UI**: Bootstrap 5 for grids, cards, and components; custom CSS for thumbnails (object-fit, gradients) and hover effects.
- **Dynamic Interactions**: HTMX for AJAX-like search-as-you-type (no full reloads); custom vanilla JS for multi-select dropdown with badges and clear functionality.
- **Template Engine**: Django templates with loops, conditionals, and filters (e.g., `truncatechars`); partials for efficient updates.

### Development Tools & Best Practices
- **Environment Management**: Virtualenv (`venv`) for isolation; VS Code with `launch.json` for debugging commands (e.g., `runserver`, `fetch_top_games`).
- **Error Handling & Debugging**: Fixed issues like null selectors, pagination bugs, and template tags (`{% load static %}`); used browser console and Django logs.
- **Static Assets**: Managed JS/CSS with Django static files; collected for production.
- **Performance**: Batched API calls (20 IDs/batch); ORM optimizations (`.distinct()` for M2M filters).

### Other Skills
- **Version Control**: Git-ready structure (e.g., `.gitignore` for `venv/`).
- **Testing & Iteration**: Rapid prototyping with incremental features (e.g., from basic table to card-based UI).
- **Documentation**: Inline comments, setup guides, and this README.

## Tech Stack
- **Backend**: Python 3.12, Django 5.x, SQLite (default; easy swap to PostgreSQL).
- **Frontend**: HTML5, Bootstrap 5, HTMX 1.9, Vanilla JS.
- **Libraries**: `requests`, `BeautifulSoup4`, `lxml` (parsing); Django contrib (admin, forms).
- **Tools**: VS Code, virtualenv.

## Setup & Installation
1. **Clone & Environment**:


2. **Django Setup**:


3. **Data Ingestion** (run once; ~5-10 min):


4. **Run the App**:

Visit `http://127.0.0.1:8000/` or `/admin/` for backend.

## Usage
- Fill filters (e.g., 2-4 players, min rating 7.0) and select mechanics (e.g., "Dice Rolling")—results update live.
- Click badges' × to remove; "Clear All" resets mechanics.
- Cards link to BGG for full details.

## Screenshots
*(Add images here for portfolio: e.g., form with badges, filtered results cards.)*

## Potential Improvements
- Pagination for results (e.g., Django's `Paginator`).
- Search by name/year via Elasticsearch.
- User auth for saved searches.
- Deployment: Docker + Heroku/AWS.

## License
MIT License—feel free to fork and adapt!

---

*Built by Adrian Jones | [My Portfolio](your-site.com) | October 2025*