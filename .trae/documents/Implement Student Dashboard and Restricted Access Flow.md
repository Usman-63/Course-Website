I have analyzed the current project structure and prepared a comprehensive plan to implement the requested changes.

### 1. New Dashboard Page (`src/pages/Dashboard.tsx`)
I will create a brand new Dashboard page exclusively for activated users.
*   **Design**: A modern, dark-mode "Student Hub" layout using a card-based grid system.
*   **Sections**:
    *   **Header**: Personalized welcome message ("Welcome back, [Name]") and a high-level progress bar.
    *   **Alerts & Updates**: The **Announcements** and **Polls** will be moved here from the Landing Page, ensuring only verified users see them.
    *   **"Up Next" Card**: A prominent section highlighting the *current* active module (the first incomplete one), with direct access to the **Video** and **Lab** links.
    *   **Curriculum Overview**: A collapsible list of all modules below, allowing users to review past content or see what's coming.

### 2. Syllabus Page Refactor (`src/pages/Syllabus.tsx`)
*   **Role Change**: This page will become the "Public Curriculum" view.
*   **Logic Update**: If a user is **activated**, accessing `/syllabus` will automatically redirect them to `/dashboard`.
*   **Content**: It will display the module list in a "read-only" or "locked" state for non-activated users, preserving the current "preview" functionality.

### 3. Landing Page Cleanup (`src/pages/Home.tsx`)
*   **Remove**: The "Latest Updates" (Announcements) and "Community Polls" sections will be removed from the public landing page.
*   **Navigation**: The "Track Progress" button will be updated to direct users to the Dashboard if they are logged in and activated.

### 4. Routing & Navigation
*   **Routes**: Add the new `/dashboard` route in `App.tsx`.
*   **Navbar**: Update the navigation menu to show "Dashboard" instead of (or alongside) "Syllabus" for activated users.

### 5. Admin & Data
*   **User Activation**: The existing `StudentManager` already allows admins to toggle `isActive`. This will now control access to the entire Dashboard.
*   **Content**: The dashboard will dynamically fetch the same course data but present it in the "unlocked" format with full video/lab access.

This approach separates the "Public Marketing" experience (Home/Syllabus) from the "Private Learning" experience (Dashboard), fulfilling all your requirements.
