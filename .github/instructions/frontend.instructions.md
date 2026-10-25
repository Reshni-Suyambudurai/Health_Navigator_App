---
name: frontend-guidelines
description: "Frontend conventions for the Angular patient health navigator application."
applyTo: "Frontend/**"
---

# Frontend Guidelines

These rules apply to frontend work under `Frontend/`.

## Project Conventions

- Keep patient FHIR API calls in the appropriate `Frontend/src/app/api/` service; place related interfaces in `Frontend/src/app/shared/types/`.
- Reuse `Frontend/src/styles.scss` for theme variables, dark mode, tables, buttons, and shared UI instead of duplicating styles.
- Reuse the shared toast service for success and error feedback.
- Add or update application routes in the relevant `route.ts` file.
- Use the existing token store for all local-storage CRUD; do not access `localStorage` directly from components.
- Place new role-specific components under `Frontend/src/app/components/roles/<role-name>/`.

## Framework and Structure

- Use Angular standalone components.
- Keep components organized by feature under `Frontend/src/app/`.
- Prefer the existing shared components, services, API clients, types, and layout primitives before adding new abstractions.
- Keep route-specific behavior in the owning feature component and shared behavior in shared services or UI components.
- Preserve existing public APIs and route paths unless the feature requires a change.

## Components and Templates

- Keep templates declarative; move business logic and data transformations into the component class or service.
- Import only the Angular standalone dependencies used by a component.
- Use typed interfaces for API responses and component state.
- Use accessible semantic elements, labels, button types, and meaningful `aria` attributes.
- Keep loading, empty, error, and disabled states visible for user-facing workflows.

## API and State

- Use the existing `UserApi` and feature API services for HTTP requests.
- Keep API calls in services rather than directly in templates or unrelated components.
- Use the existing session and toast utilities for authentication state and user feedback.
- Use the active user data from `tokenstore` for API identity parameters when needed; do not hardcode user IDs,origanization_id,role_id2,name or email in the code.
- Treat optional backend values defensively and provide clear fallback text in the UI.

## Styling

- Follow the shared variables and theme definitions in `Frontend/src/styles.scss`.
- Use `var(--table-bg)` as the polished-white background for tables, forms, and cards displayed in body content.
- Use component SCSS for local layout and presentation; add styles to `styles.scss` only when they are genuinely shared.
- Support both light and dark themes by using CSS custom properties instead of hardcoded surface, text, border, and muted colors.
- Preserve responsive behavior for desktop and mobile viewports.
- Avoid unrelated formatting or broad visual refactors when changing a feature.

## Validation

- Run editor diagnostics for changed TypeScript, HTML, and SCSS files.
- Run the Angular development or production build after component, template, routing, or shared-style changes.
- Check affected workflows for loading, error, responsive, and theme behavior when practical.
