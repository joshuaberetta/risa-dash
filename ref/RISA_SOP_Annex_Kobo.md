| RISA SOP: Annex F. Data collection with KoboToolbox (technical annex) |
| :---- |

*Working draft v3 · 12 November 2026 · annex to the RISA SOP v3 · owner: Kobo*

| NOTE FOR THE WORKING GROUP This annex is for the data / Kobo focal point. It replaces "Kobo for dummies". It is technical but not click-by-click: each topic says what to do, why, how in outline, and how it most commonly fails, then links to the official KoboToolbox or ODK documentation, which is kept up to date by the people who build the software. The form itself (questions, codes, country checklist, change rules) is in Annex A. **"Kobo for dummies" published a shared username and password. Change that account's password now, and do not circulate that guide again.** |
| :---- |

**Contents**

1. Platform-neutral principle
2. Accounts and ownership
3. Setting up from the template
4. Testing before fieldwork
5. Devices
6. Collection rules
7. Changing the form mid-mission
8. Daily quality review
9. Exports and the API
10. Connecting the RISA dashboard
11. Media and bandwidth
12. Data protection
13. The feedback form
14. Closing, archiving and handover
15. Optional: doing these tasks with an AI assistant (kobo-mcp)
16. Troubleshooting

Official documentation used throughout:

* KoboToolbox support: https://support.kobotoolbox.org/

* ODK documentation: https://docs.getodk.org/

* XLSForm reference: https://xlsform.org/en/

# **1. Platform-neutral principle**

**What.** The RISA form is a standard XLSForm. It runs on KoboToolbox, ODK Central, Ona or any other XLSForm server, and on KoboCollect, ODK Collect or a web form.

**Why.** The host may already use one platform, or may need its data on a national server. RISA should not force a change of software.

**How.** This annex uses KoboToolbox as the worked example, because the partners use it. The same steps exist on other platforms under other names. On ODK Central, for example, "App Users" and their QR codes replace per-collector accounts on the device.

**Common failure.** A country edits the form in a platform's own form builder and the names drift from the codebook. Edit the XLSForm, keep the names, and upload it.

Links: KoboToolbox, Using XLSForm with KoboToolbox: https://support.kobotoolbox.org/xlsform_with_kobotoolbox.html · ODK Central: https://docs.getodk.org/central-intro/ · Ona help: https://help.ona.io/

# **2. Accounts and ownership**

**What.**

* The project is owned by an organisation account of the deploying partner (a KoboToolbox Team account where the partner has one), or by the host NDMA's own account. Never by a person's own account.

* Each collector has their own account, shared on the project with **Add submissions** only. Reviewers get **View submissions** and **Validate submissions**. Only the data focal point and a back-up can edit the form.

* No shared logins.

* Never write a password, API token or settings QR code into a document, slide, chat, screenshot or shared spreadsheet.

* Choose the server for data residency: the Global server or the EU server (hosted in the EU), or a national or organisational server. Agree it with the host in the data-sharing agreement. Accounts and projects cannot move between servers by transfer; moving means redeploying the form and migrating the data.

**Why.** A shared login hides who collected what, cannot be withdrawn from one person, and ends up in a guide. A project on a person's account leaves with that person. The Madagascar lesson (SOP §3.7): a dashboard left on the deploying team's credentials was hard to unwind.

**How.**

1. Create or choose the owner account on the agreed server. Turn on two-factor authentication.

2. Create one account per collector, or ask each collector to create their own on the same server.

3. Share the project with each account at the right permission level. For larger teams, use bulk sharing or row-level permissions (reviewers who see only their own team's records).

4. Keep the list of accounts and their permissions (the access list, §12).

**Common failure.** The deploying team creates the project on whichever account is open on the laptop. At handover nobody can transfer it. Decide the owner account before the first upload.

Links: Creating a KoboToolbox account (Global and EU servers): https://support.kobotoolbox.org/creating_account.html · Sharing projects with user-level permissions: https://support.kobotoolbox.org/managing_permissions.html · Using the Team management feature (Teams and Enterprise plans): https://support.kobotoolbox.org/team_management_feature.html · Setting up two-factor authentication: https://support.kobotoolbox.org/two_factor_authentication.html

# **3. Setting up from the template**

**What.** Adapt the template for the country (Annex A §3), then create and deploy the project.

**Why.** Starting from the template, not from the last country's form, keeps the names and codes the dashboard and the GIS team expect.

**How.**

1. Work through the country checklist in Annex A.

2. Upload the XLSForm to create a new project on the owner account. Give it a clear name, e.g. "RISA – Bahamas – 2026".

3. Deploy it.

4. Share it with the collector and reviewer accounts (§2).

Alternatively, clone an existing RISA project and replace its form with the country's file.

**Common failure.** The form is built in the web form builder "to save time", and question names become auto-generated codes. Always upload the XLSForm.

Links: Deploying forms for data collection: https://support.kobotoolbox.org/deploy_form_new_project.html · Introduction to XLSForm: https://support.kobotoolbox.org/edit_forms_excel.html

# **4. Testing before fieldwork**

**What.** Test the form on the devices the team will use, offline, before the first real observation. Then freeze it.

**Why.** Errors found on day one in the field cost a day; errors found after collection cost the data.

**How.**

1. Preview the form in the browser. Check every feature type shows the right detail questions.

2. Do a dry run on a real device with the network off: open the form, fill one observation of each type you use, take a GPS point and photos, finalise, then switch the network on and send.

3. Look at the test data in the data table and in an export. Check the column names match the codebook.

4. Delete the test data, or mark it **Not Approved**, before real collection starts.

5. Freeze the form. From now on, changes follow the rules in Annex A §4 and §7 below.

**Common failure.** Test submissions stay in the project and appear on the first map. Delete them or mark them Not Approved.

Links: Viewing and validating your data: https://support.kobotoolbox.org/viewing_validating_data.html · Editing and deleting your data: https://support.kobotoolbox.org/editing_deleting_data.html

# **5. Devices**

**What.** Android phones or tablets with KoboCollect (or ODK Collect). The offline web form (Enketo) on an iPhone, iPad or laptop is the fallback.

**Why.** KoboCollect works fully offline, records the audit log and handles GPS and photos best. Web forms work on any device but do not record the audit log.

**How.**

* **Server.** Configure the first device with the KoboCollect URL of the chosen server (Global: `https://kc.kobotoolbox.org`, EU: `https://kc-eu.kobotoolbox.org`) and the collector's own account.

* **Settings QR code.** To copy the settings to other devices, use the device's settings QR code. It contains the server, username and password in plain text. Either remove the password from the code before sharing it, so each collector enters their own, or make one code per collector. Treat any settings QR code as a password.

* **Form updates.** Set "Blank form update mode" to update automatically ("Exactly match server", or "Previously downloaded forms only" with automatic download), so a redeployed form reaches every device.

* **Auto send.** Turn on auto send over Wi-Fi only where mobile data is expensive or slow; over Wi-Fi and cellular where it is not.

* **GPS.** The form captures at 5 m accuracy and warns above 10 m (Annex A). Turn on high-accuracy location on the device. Let collectors take a test point at the first site.

* **Image size.** The form caps photos at 1600 px. The device's image-size setting can reduce them further if bandwidth is very poor.

* **Username.** Check the username is set, so each record carries who collected it.

* **Power.** Carry power banks and a vehicle charger. Frequent automatic form updates and high-accuracy GPS drain the battery.

* **Fallback.** For iOS or laptops, use the web form link that works online and offline ("Online-Offline (multiple submission)"). Open it once while online so it is cached. Do not clear the browser's cache or site data during collection, or saved drafts are lost.

**Common failure.** One device is set up with the owner account and its QR code is copied to every tablet, so every record is "submitted by" the owner and the password travels with the code. Use collector accounts.

Links: Setting up the KoboCollect app: https://support.kobotoolbox.org/kobocollect_on_android_latest.html · Customizing KoboCollect settings: https://support.kobotoolbox.org/kobocollect_settings.html · Collecting data using web forms: https://support.kobotoolbox.org/data_through_webforms.html · ODK Collect settings QR codes: https://docs.getodk.org/collect-import-export/ · ODK Collect settings: https://docs.getodk.org/collect-settings/

# **6. Collection rules**

**What.** The rules collectors follow, in the briefing before the first site. The reasons are in SOP §2.1.

* One object, one form. Finalise and start a new form for the next object.

* Observe, don't ask. If you cannot check it, answer "Can't see".

* Stand at the object for the GPS point. Wait for the accuracy; place the pin on the map only if the GPS will not settle.

* Photograph the object, not people.

* Use the feature ID agreed for the site (e.g. WP-01, WP-02).

* Put anything else in the note.

* Send whenever there is a connection, and every evening.

* Your location is logged while a form is open (the audit log). Tell collectors.

**Common failure.** Collectors keep forms as drafts "to finish later" and never finalise them. Finalise at the object.

Links: Collecting data using KoboCollect: https://support.kobotoolbox.org/data_collection_kobocollect.html · GPS questions in KoboToolbox: https://support.kobotoolbox.org/gps_questions.html · Collecting GPS data with KoboToolbox: https://support.kobotoolbox.org/collect_gps.html · Audit metadata: https://support.kobotoolbox.org/form_meta.html · ODK form audit log: https://docs.getodk.org/form-audit-log/

# **7. Changing the form mid-mission**

**What.** Sometimes a change cannot wait: a missing site, a new organisation, a confusing label.

**Why.** Every change creates a new form version. Additive changes join cleanly; renames and deletions break the data.

**How.**

1. Apply the change rules in Annex A §4: add only, never rename or delete a name or code, bump the version.

2. Replace the form in the existing project with the new XLSForm and redeploy. Do not create a new project: the data stays in one place.

3. Ask collectors to send all finalised forms first, then update the form on their devices (automatic if set up as in §5).

4. Record the change in the deployment log and tell the remote GIS owner.

Adding a site, an organisation or a language is safe. Adding a feature type also needs a map symbol (Annex A §3, step 5).

**Common failure.** A new project is created for the changed form. Data splits across two projects and the dashboard only reads one.

Links: Deploying forms for data collection (redeploying): https://support.kobotoolbox.org/deploy_form_new_project.html · ODK, managing form versions in Central: https://docs.getodk.org/central-forms/

# **8. Daily quality review**

**What.** Every evening, the data focal point reviews the day's records and gives collectors feedback before they go out again.

**Why.** Collectors can still fix an error the next morning. A week later they cannot.

**How.**

1. **Is everything in?** Compare the day's count per collector with what they say they collected. Chase unsent forms.

2. **Data table.** Read through the day's records. Check sector and type match the photo, status is answered, and notes make sense.

3. **Validation status.** Mark each record: **Approved** (checked), **On hold** (question for the collector), **Not Approved** (test, duplicate or wrong). Products leave out Not Approved records. The RISA dashboard shows the validation status with each record but does not yet hide Not Approved ones (TBC); delete true duplicates and test records, or keep them out of the dashboard's layer.

4. **Duplicates.** Look for the same feature ID twice, or the same type at nearly the same point at the same site.

5. **GPS accuracy.** Check records with accuracy above 10 m and those placed by hand (`obs/location_method` = `manual`) against the imagery.

6. **Photos.** Check for faces and remove any that slip through (§12).

7. **Feedback.** Brief collectors the next morning: what was good, what to fix, which records are on hold.

8. **Back up.** Export a full copy at the end of the day (§9).

**Common failure.** Review is left to the GIS team at the end of the mission. Do it daily.

Links: Viewing and validating your data: https://support.kobotoolbox.org/viewing_validating_data.html · Editing and deleting your data: https://support.kobotoolbox.org/editing_deleting_data.html

# **9. Exports and the API**

**What.** Ways to get the data out.

| Need | Use |
| :---- | :---- |
| Analysis, the codebook's names | XLS or CSV export with **XML values and headers**, so columns are the question names and answers are the codes. Keep group names in headers (`obs/status`). |
| Reading by people | XLS export with labels. |
| GIS | GeoJSON export. KML still exists but KoboToolbox will drop it; prefer GeoJSON. |
| A live link for Excel, Power BI or QGIS | Synchronous export links (CSV or XLSX), which always return the latest data. |
| Automation | The KoboToolbox REST API (v2), with an API token. |
| Pushing each submission elsewhere | REST services (webhooks). |
| Media | Attachments downloaded with the export, or through the API. |

**Why.** A standard export keeps the names from the codebook, so the GIS template and any analysis read it without re-coding.

**How.** Keep tokens out of documents. An API token gives full access to its account, like a password. Use the token of a dedicated view-only account for anything automatic (§10). Store tokens in a password manager or the receiving tool's settings, never in a script, a shared spreadsheet or a synced export URL pasted into a document. Rotate the token if it leaks.

**Common failure.** A label export is fed into GIS and the codes do not match the symbology. Use XML values and headers.

Links: Exporting and downloading your data: https://support.kobotoolbox.org/export_download.html · Advanced options for exporting data: https://support.kobotoolbox.org/advanced_export.html · Using the API for synchronous exports: https://support.kobotoolbox.org/synchronous_exports.html · Getting started with the API: https://support.kobotoolbox.org/api.html · Using the REST services: https://support.kobotoolbox.org/rest_services.html

# **10. Connecting the RISA dashboard**

**What.** The RISA dashboard reads the project directly and keeps the map up to date.

**Why.** A connected project puts new observations on the map within minutes, without anyone exporting files.

**How.**

1. Create a dedicated account (e.g. one per deployment) and share the project with it at **View submissions** only.

2. Sign in as that account and copy its API token (Account settings, Security).

3. In the dashboard, connect the project with that token and the server. The dashboard stores the token encrypted and never shows it to the browser.

4. A RISA form maps itself (Annex A §5). Check the first records appear with the right symbols and colours.

5. At handover, transfer or remove the connection with the project (§14).

Dashboard guide: https://risa-dash.kobolabs.dev/guide/

**Common failure.** The dashboard is connected with the data focal point's own token. When that person leaves, or changes the password or token, the map stops updating, and their full account access sits in the dashboard.

# **11. Media and bandwidth**

**What.** Photos and voice notes are most of the data volume.

**Why.** Field connections are slow and expensive. Large photos block the sync of the forms behind them.

**How.**

* Keep the 1600 px cap in the form. Reduce the device image size further only if needed.

* Up to three photos per observation is a maximum, not a target.

* Keep voice notes short; prefer a typed note.

* Send over Wi-Fi at the base each evening if mobile data is poor (§5).

* Export data without media for quick checks; download attachments in bulk on a good connection.

* Check the account's storage and submission limits before the mission.

**Common failure.** Devices queue hundreds of full-size photos and nothing sends on a weak connection.

Links: Media questions in KoboToolbox: https://support.kobotoolbox.org/photo_audio_video_file.html · Managing respondent-submitted media: https://support.kobotoolbox.org/managing_media_responses.html · Managing account usage limits: https://support.kobotoolbox.org/account_usage_limits.html

# **12. Data protection**

**What.** The technical side of SOP §3.8.

* **Data-sharing agreement.** Signed with the host before collection: owner, who may see the data, server and data residency, retention, deletion. Template text TBC.

* **Sensitive locations.** Agree with protection actors which types (safe spaces for women and girls, child-friendly spaces, some health and protection services) appear on public products, only on restricted ones, or not at all. Restrict who can view those records, for example with row-level permissions, and leave them out of public exports.

* **Photos.** No identifiable faces, children or vulnerable people. Delete any that slip through.

* **Access list.** Who has which permission on the project, the storage and the dashboard. Review at each rotation. Remove people who have left.

* **Devices.** Screen lock on every device. Delete sent forms from devices at the end of the mission.

* **Retention and deletion.** At closure, export a full archive for the host, then delete or transfer the working copies (§14). Default retention period TBC.

**Why.** Locations of services for women, children or survivors can put people at risk if they reach the wrong hands.

**Common failure.** The project is made public "so partners can see it". Share with named accounts, or share products, not the raw data.

Links: Data security and protection in KoboToolbox: https://support.kobotoolbox.org/is_my_data_safe.html · Data storage: https://support.kobotoolbox.org/data_storage.html · Compliance with GDPR: https://support.kobotoolbox.org/gdpr.html · Sharing projects with project-level settings: https://support.kobotoolbox.org/project_sharing_settings.html · Encrypting forms: https://support.kobotoolbox.org/encrypting_forms.html

# **13. The feedback form**

**What.** A short form for map users, linked by a QR code on every RISA map (SOP §2.6).

**Why.** RISA needs to know whether the maps were used and what was missing.

**How.** Kobo builds the form by the end of 2026. Its questions, its owner account and whether answers are anonymous are TBC. It should live on a project owned by the partnership, not by one deployment, so it outlives each handover. The RISA dashboard prints its QR code on page 1 when a feedback link is set.

**Common failure.** The feedback link points to a deployment project that is archived at handover. Use the partnership's project.

# **14. Closing, archiving and handover**

**What.** What to do when collection ends or the site is handed over.

**How.**

1. **Final review.** Finish validation (§8).

2. **Archive the data.** Export XLS (XML values and headers), GeoJSON and the media. Download the form as XLSForm. Store them in the agreed archive with the codebook.

3. **Transfer ownership** of the project to the receiving organisation's account, if agreed. Both accounts must be on the same server. Check the receiving team can open it before leaving.

4. **Remove access** for the deploying team's collectors and reviewers, except those the receiving organisation asks to keep.

5. **Dashboard.** Replace the dashboard's token with one from the receiving organisation, or disconnect it.

6. **Archive the project** to stop new submissions while keeping the data. Delete it only when the data-sharing agreement says so, after the archive is checked. Deleted projects cannot be recovered.

7. **Devices.** Delete sent forms and remove the project from devices.

**Common failure.** The project is archived on the deploying team's account and the host has no copy.

Links: Managing projects in KoboToolbox (archiving and deleting): https://support.kobotoolbox.org/managing_projects.html · Transferring ownership of a project: https://support.kobotoolbox.org/project_sharing_settings.html

# **15. Optional: doing these tasks with an AI assistant (kobo-mcp)**

**What.** kobo-mcp is a remote MCP server that lets an AI assistant (Claude or another MCP client) work with KoboToolbox projects: https://mcp.kobolabs.dev/mcp. Setup instructions: https://mcp.kobolabs.dev. It is optional; every task below can be done by hand.

**How it connects.** Each person connects with their own KoboToolbox API token through the server's sign-in page. The assistant sees what that account can see and acts as that account, so the permissions in §2 still apply. Tools that change data are marked as write tools, and the assistant is told to confirm with you before redeploying a live form, changing records in bulk, sharing a project or archiving it. Several tools offer a dry run.

| Task | Tools |
| :---- | :---- |
| Check a country form before upload | `convert_xlsform` (converts the XLSForm as KoboToolbox would and reports errors); `preview_form` (fill it in inside the chat) |
| Start a country form from the template or an existing RISA project | `clone_project`, then `deploy_form` with the country's file |
| Deploy, or redeploy a change | `deploy_form`; `compare_form_versions` to see what changed |
| Share with collectors | `share_project`, `bulk_share_project` (with a dry run); `list_permissions` for the access list |
| Daily review | `summarize_submissions` (missing answers, choice counts, map extent, per collector); `find_duplicates`; `set_validation_status` (by ids or filter, dry run first); `get_submission_stats` |
| Exports and closing | `create_export` (XLSX, CSV, GeoJSON, KML); `archive_project` |

Example: *"For the RISA Bahamas project, summarise today's submissions by collector, list possible duplicates and any record with GPS accuracy above 10 m, and mark the duplicates Not Approved after I confirm."*

**Data protection.** The assistant sends what it reads to the AI provider. Use it on RISA data only if the data-sharing agreement allows, and not on restricted records (§12). Connect an account with only the permissions the task needs. Never paste a token into the chat.

**Common failure.** The assistant is connected with the owner account for a read-only task. Use a reviewer account.

# **16. Troubleshooting**

| Problem | Likely cause | What to do |
| :---- | :---- | :---- |
| Upload refused: "label" and "label::English (en)" | Mixed language columns | Give every label, hint and constraint message column a language suffix (Annex A §3, step 6). |
| Districts or sites list is empty | Parent column missing or P-code mismatch | Check each `level_2` row has its `level_1` P-code, and each site its `level_2` P-code. |
| The form on devices is out of date | Devices update manually | Set automatic form updates (§5), or "Get blank form" on each device. |
| "Submitted by" is the same for everyone | Shared login or a copied QR code | One account per collector (§2, §5). |
| Forms stuck in "Ready to send" | No connection, or Wi-Fi-only auto send | Connect to Wi-Fi at the base, or send manually. Check the account still has Add submissions. |
| Authentication error on send | Wrong account, changed password, or permission removed | Re-enter the collector's own credentials; check the project's sharing. |
| GPS will not settle | Indoors, under trees, high-accuracy off | Step outside, turn on high-accuracy location, wait; else place the pin on the map. |
| Points cluster in one place | Points taken from the vehicle or entrance | Brief collectors again; check against imagery in the daily review. |
| Photos missing in the export | Media still uploading, or exported without media | Wait for devices to finish sending; download attachments separately. |
| Web form drafts lost | Browser cache cleared | Do not clear site data during collection; send drafts as soon as possible. |
| No audit log in some records | Records came from the web form | Expected: web forms do not record the audit log. |
| Export columns do not match the codebook | Label export, or group names dropped | Export with XML values and headers, keeping group names. |
| Dashboard map stopped updating | Token changed, account removed, or project archived | Reconnect with a valid view-only token (§10). |
| Two projects for one deployment | A changed form was uploaded as a new project | Use one project; merge exports with the legacy mapping if needed, and replace the form in place next time (§7). |
