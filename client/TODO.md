# Frontend TODO (1-week MVP)

This file lists a small, prioritized set of tasks to finish the front-end in ~1 week. I've focused on the essential user flows so you can demo bookings, schedules, and basic barber management quickly.
# Frontend TODO (1-week MVP)

This file lists a small, prioritized set of tasks to finish the front-end in ~1 week. I've focused on the essential user flows so you can demo bookings, schedules, and basic barber management quickly.

How to use

- Complete items top-down (MVP items first).
- Mark items done or move lower-priority items to a stretch list if time is short.

---

## MVP (must-have)

1. Setup front-end dev environment (1–2 hours)
   - cd `client/barber-front`, run `npm install` (or `yarn`) and `npm run dev`.
   - Ensure API base URL is configured (use an env file or vite define).
   - Acceptance: site runs locally and connects to backend endpoints.

2. Authentication (4–6 hours)
   - Wire `Login` and `SignUp` components to backend auth (token stored in localStorage).
   - Redirect to home on successful login; fetch user profile.
   - Acceptance: user can sign up and log in; Nav shows user state.

3. Navbar & routing (1–2 hours)
   - Implement main routes: Home, Services, Barbers, My Appointments, Login/SignUp.
   - Show role-based links (barber dashboard if barber).
   - Acceptance: navigation works; routes protected where needed.

4. Services list & booking CTA (4 hours)
   - GET `/api/services/` and display list cards (name, duration, price, short desc).
   - 'Book' opens booking modal that pre-selects the service.
   - Acceptance: user can view services and start booking flow.

5. Barbers list & basic profile (3 hours)
   - GET `/api/profiles/barbers/` (or `/api/barbers/`) to list barbers with avg rating.
   - Barber detail modal shows rating and a 'Book' button.
   - Acceptance: user can see barbers and open detail for booking.

6. Booking flow (Priority — 8–12 hours)
   - Booking form fields: service, barber, date/time, duration (prefill from service).
   - Call `POST /api/appointments/check_availability/` to validate slot.
   - If available, call `POST /api/appointments/` to create the appointment.
   - Show confirmation and error handling (conflicts, off-hours).
   - Acceptance: user can successfully create a booking and see confirmation.

7. My Appointments (3–4 hours)
   - Upcoming and History pages: `GET /api/appointments/upcoming/` and `GET /api/appointments/history/`.
   - Support Cancel and Reschedule: call `PATCH /api/appointments/{id}/cancel/` and `/reschedule/`.
   - Acceptance: user sees their appointments and can cancel/reschedule.

8. Ratings (2–3 hours)
   - After a completed appointment allow user to POST `/api/ratings/`.
   - Show recent reviews on barber profile.
   - Acceptance: user can submit a rating and it appears under barber.

---

## Important secondary features (if time permits)

9. Payments (minimal) (1–2 hours)
   - Show payment status on appointment detail.
   - Provide a fake payment flow or admin action to mark paid (PATCH `/api/payments/{id}/mark_paid/`).
   - Acceptance: payment status visible; demoable flow exists.

10. Barber dashboard (basic) (3–4 hours)
    - For barber users: list upcoming appointments, mark completed.
    - Acceptance: barber can view and act on appointments.

11. Polish & mobile tweaks (2–4 hours)
    - Minor UI cleanups, responsive layout, colors, small UX fixes.
    - Acceptance: app presentable for demo on phone and desktop.

---

## Stretch / Optional (only if everything above is done)

- Real-time notifications (WebSockets / Django Channels).
- Google Calendar sync UI to show synced events (call `/api/calendar-events/sync/`).
- Full payment gateway integration (Stripe/PayPal) instead of placeholder.
- More analytics pages for admin (bookings per day, revenue).

---

## API quick reference (useful endpoints)

- GET `/api/services/` — list services
- GET `/api/profiles/barbers/` — list active barbers with stats
- POST `/api/appointments/check_availability/` — check slot
- POST `/api/appointments/` — create appointment
- GET `/api/appointments/upcoming/` — upcoming
- GET `/api/appointments/history/` — past
- PATCH `/api/appointments/{id}/cancel/` — cancel
- PATCH `/api/appointments/{id}/reschedule/` — reschedule
- POST `/api/ratings/` — create rating
- PATCH `/api/payments/{id}/mark_paid/` — mark payment (admin)
- POST `/api/calendar-events/sync/` — sync appointment to external calendar

---

Notes & recommendations

- Keep forms simple; validate on client then rely on server-side checks for conflict rules.
- Favor clear success/error messages for each API step (availability, booking, cancel).
- If time is tight, postpone payments and calendar sync — they are not required to demonstrate booking flow.

Good luck — tell me which item you want me to help implement first and I will create components or code snippets for it.

