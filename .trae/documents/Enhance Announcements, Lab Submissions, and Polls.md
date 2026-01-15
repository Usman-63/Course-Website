I will implement the requested features to enhance the Announcements, Lab Submissions, and Polls functionality.

### 1. Make Announcements More Prominent
*   **Dashboard Layout Update:** Move the Announcements section to the top of the Dashboard, spanning the full width, to ensure it is the first thing students see.

### 2. Lab Submissions (Multiple Labs per Module)
*   **Data Structure:** Update the `CourseModule` interface to include a `labCount` field (defaulting to 1).
*   **Admin Interface:** Update `ModuleEditor.tsx` to allow admins to specify the number of labs for each module.
*   **Student Interface:** Update `Dashboard.tsx` to render multiple submission input fields based on the module's `labCount`.
*   **Submission Storage:** Update the submission logic to store multiple links per module using a structured format (e.g., nested objects or suffixed keys in Firestore).

### 3. Poll Improvements
*   **Data Tracking:** Modify the voting logic in `Dashboard.tsx` to record *who* voted for what by adding a `votes` array to the poll document (containing user ID, name, and selected option).
*   **Admin Interface:** Update `PollManager.tsx` to:
    *   Display a detailed breakdown of votes (showing which student voted for which option).
    *   Add a "Download CSV" button to export the poll results.

### 4. Code Adjustments
*   **Student Manager:** Update `StudentManager.tsx` to correctly display multiple submission links for each student.
*   **API:** Update `api.ts` to reflect the new module structure.
