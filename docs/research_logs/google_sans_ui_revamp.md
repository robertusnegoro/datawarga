# Research Log: Google Cloud Web Console Font & UI Revamp

## 1. Font Stack of Google Cloud Web Console
Based on documentation and web requests, the typography of the Google Cloud Web Console (`console.cloud.google.com`) is characterized by:
- **Primary Typeface**: `Google Sans` (a geometric sans-serif typeface designed by Google, primarily for headings and branding).
- **Secondary Typeface / Fallback**: `Roboto` (an open-source sans-serif developed by Google, optimized for UI readability across various screen sizes).
- **Monospace Typeface**: `Google Sans Code` or `Roboto Mono` (used for code blocks, terminal outputs, and data values).
- **Font Stack in CSS**:
  ```css
  font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  ```

## 2. Technology Stack & UI Architecture
- **Framework**: Django (Python web framework) serving server-side templates.
- **CSS Framework**: Bootstrap (loaded via CDN or local assets, customized in `kependudukan/static/dashboard/dashboard.css`).
- **Base Templates**:
  - `base.html`: The core shell containing the sidebar navigation, top header, and page container for authenticated users.
  - `base_plain.html`: A stripped-down shell without navigation, used for public pages (e.g., `public/iuran.html`).
- **Auth Templates**:
  - `registration/login.html`: Standalone sign-in page.
  - `registration/logged_out.html`: Standalone signed-out page.

## 3. Revamp & Aesthetics Strategy
- **Aesthetic Direction**: Premium modern dashboard style. Integrate Google Cloud UI concepts (clean borders, GCP Blue `#1a73e8`, subtle gridlines, elevation shadows) with high-end modern design trends (glassmorphism card, mesh gradient background, custom inputs).
- **Typography Integration**:
  - Load `Roboto` and `Roboto Mono` from Google Fonts API globally via link tags in `base.html` and `base_plain.html`.
  - Set the default font-family in `dashboard.css` to `'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`.
  - Set code and pre elements to use `'Google Sans Code', 'Roboto Mono', monospace`.
- **Login/Logout Revamp**:
  - Refactor both templates to extend `base_plain.html` so they automatically inherit the global style rules, fonts, and assets.
  - Wrap the content in a beautiful card using glassmorphism styling (`backdrop-filter: blur(12px)`, semi-transparent background and border, soft shadow).
  - Use custom floating label inputs that change color to GCP blue (`#1a73e8`) when active.
  - Add a gorgeous background with a subtle, premium mesh gradient.
  - For the logout page, add a clean confirmation screen with a "Sign In Again" action button.
