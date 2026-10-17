# Frontend Architecture Guide

This frontend follows a scalable Angular standalone architecture designed for larger feature growth.

## Folder Structure

```text
src/
	app/
		core/        # app-wide singleton providers, interceptors, guards, config
		features/    # business features grouped by domain
			auth/
				pages/
					login/
			home/
				pages/
					home/
		shared/      # reusable UI and utilities used by multiple features
			ui/
				toast/
		app.config.ts
		app.routes.ts
		app.ts
		app.html
```

## Frontend Rules

1. Keep business logic inside feature folders only.
2. Keep reusable widgets in shared and avoid feature-to-feature direct imports.
3. Keep app-wide concerns in core (auth/session state, API clients, interceptors).
4. Keep routes centralized in app.routes.ts until feature route files are required.
5. Use SCSS only for style files.
6. Use the design token primary color #1aa3ff for action and focus states.
7. Add tests for each new standalone component page.

## Commands

```bash
npm install
npm start
npm run build
npm test
```

## Next Recommended Additions

1. Add core API client services in src/app/core/api.
2. Add auth guard and route protection for private pages.
3. Add state management per feature only when feature complexity requires it.
