# XState Workflow

A state machine-based workflow engine for Frappe Framework, featuring a visual drag-and-drop builder, XState-compatible execution, and a comprehensive approval system.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Frappe Framework | 14.0+ | ERPNext optional |
| Python | 3.10+ | Required for type hints |
| Node.js | 18+ | For frontend build |
| pnpm | 8+ | Package manager |
| MariaDB | 10.6+ | Database |

## Installation

### Step 1: Get the App

```bash
# Navigate to your bench directory
cd ~/frappe-bench

# Get the app from repository
bench get-app https://github.com/your-org/xstate_workflow.git
```

### Step 2: Install on Site

```bash
# Install the app on your site
bench --site your-site.local install-app xstate_workflow
```

### Step 3: Build Frontend Assets

```bash
# Navigate to frontend directory
cd apps/xstate_workflow/frontend

# Install dependencies
pnpm install

# Build all packages
pnpm build
```

### Step 4: Clear Cache and Restart

```bash
# Clear Frappe cache
bench --site your-site.local clear-cache

# Restart the bench
bench restart
```

### Step 5: Verify Installation

1. Log into your Frappe site
2. Navigate to `/xstate-builder` in your browser
3. You should see the workflow builder interface

**Verification Checklist:**
- App installed: `bench --site [site] list-apps`
- Frontend built: Check for `dist/` folders in `frontend/`
- Builder accessible: Visit `/xstate-builder`
- DocTypes created: Check Desk > State Machine

## Documentation

For comprehensive documentation, see [docs/MANUAL.md](docs/MANUAL.md).

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/xstate_workflow
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

## License

MIT

## Screenshots

### Simple For Users
<img width="949" height="475" alt="Workflow Builder Interface" src="https://github.com/user-attachments/assets/fe538831-835d-4e2e-a379-d090e10b3895" />
