# Frontend Setup - Quick Reference

## Complete Setup Checklist

### Phase 1: Project Initialization
- Next.js 14 project created with TypeScript
- Dependencies installed
- Folder structure created
- Configuration files present:
  - `next.config.js`
  - `tailwind.config.ts`
  - `tsconfig.json`
  - `.eslintrc.json`
  - `postcss.config.js`
  - `.prettierrc`

### Phase 2: Environment & Styles
- Copy `.env.example` to `.env.local`
- Fill in the API and Stripe values for your local setup
- Global styles live in `src/app/globals.css`
- Root layout lives in `src/app/layout.tsx`

### Phase 3: Core UI Components
Current shared UI components live in `src/components/ui/` and are ready for use.
No extra local `progress.tsx` or `switch.tsx` files are required for setup.

### Phase 4: Types & API Layer
- Type definitions live in `src/types/`
- API client lives in `src/lib/api/client.ts`
- Auth and billing services live under `src/lib/api/`

### Phase 5: State Management
- Zustand store lives in `src/stores/`
- Custom hooks live in `src/hooks/`

### Phase 6: Utilities & Pages
- Utilities live in `src/lib/`
- Landing page and dashboard routes live under `src/app/`

## File Structure Summary

```
frontend/
├── src/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   ├── stores/
│   └── types/
├── public/
├── .env.local               # Environment variables (create locally)
├── .env.example             # Example environment file
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── README.md
```

## Connection to Backend

The frontend uses the backend API at:

```
http://localhost:8000/api/v1
```

## Troubleshooting

- Verify the backend is running on `http://localhost:8000`
- Check `.env.local` has the correct `NEXT_PUBLIC_API_URL`
- Stripe test webhooks should be forwarded to `/api/v1/webhooks/stripe`
