# Urgency: what to change in Power Apps Studio

Every change below is a **property edit on a control that already exists**. Nothing
is added, deleted, moved or resized, so your layout work is untouched.

**26 property edits across 6 screens.** `scrNewRFQ` and `scrAdminUsers` need nothing.

For each one: select the control in the tree, pick the property named in the heading
from the dropdown at the top left of the formula bar, select all in the formula bar,
and paste. The formulas are exactly as committed to `2-9-26-SHQ`.

Do the two `OnVisible` edits and the two Refresh buttons **first** — every other
change on those screens reads `UrgRank`, and will show as an error until the field exists.

---


## scrBuyerQueue

### 1. Screen `scrBuyerQueue`  ·  **OnVisible**

Builds the queue with two extra fields on every row: **DaysLeft** and **UrgRank**. Everything else on this screen reads those.

```powerfx
Set(varBqDenied, false);
Set(varBqDenied, varRole <> "Buyer" && varRole <> "Admin");
If(
    varBqDenied,
    Notify("Buyer access only. Taking you back to the home screen.", NotificationType.Error, 4000),
    Refresh(RFQ);
    // Urgency is worked out from the due date each time this loads, so a request
    // raised weeks ahead still climbs the list as its due date approaches.
    //   0 overdue | 1 due today | 2 due within 3 days | 3 later | 8 no date | 9 closed
    ClearCollect(
        colBuyerRFQs,
        AddColumns(
            AddColumns(
                RFQ,
                DaysLeft, If(IsBlank(RFQduedate), 9999, DateDiff(Today(), RFQduedate, TimeUnit.Days))
            ),
            UrgRank,
                If(
                    'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], 9,
                    IsBlank(RFQduedate), 8,
                    DaysLeft < 0, 0,
                    DaysLeft = 0, 1,
                    DaysLeft <= 3, 2,
                    3
                )
        )
    );
    Set(varConfirmAction, Blank());
    Set(varSaving, false);
    Reset(txtBqSearch);
    Reset(tglBqShowClosed);
    Reset(cboBqSort)
)
```

### 2. `btnBqRefresh`  ·  **OnSelect**

Same rebuild behind the Refresh button, so pressing it re-dates the bands. Miss this one and Refresh silently strips the new fields, blanking the urgency column.

```powerfx
Refresh(RFQ);
ClearCollect(
    colBuyerRFQs,
    AddColumns(
        AddColumns(
            RFQ,
            DaysLeft, If(IsBlank(RFQduedate), 9999, DateDiff(Today(), RFQduedate, TimeUnit.Days))
        ),
        UrgRank,
            If(
                'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], 9,
                IsBlank(RFQduedate), 8,
                DaysLeft < 0, 0,
                DaysLeft = 0, 1,
                DaysLeft <= 3, 2,
                3
            )
    )
);
Notify("Queue refreshed.", NotificationType.Success, 2000)
```

### 3. `lblBqCounts`  ·  **Text**

Adds a *Due within 3 days* counter, and fixes the overdue count, which previously also counted RFQs with no due date at all.

```powerfx
"Waiting on you: " & CountRows(Filter(colBuyerRFQs, AwaitingAction.Value = "Buyer")) &
"     ·     Out with vendors: " & CountRows(Filter(colBuyerRFQs, 'RFQ status'.Value = "RFQ sent out")) &
"     ·     Due within 3 days: " & CountRows(Filter(colBuyerRFQs, UrgRank = 1 || UrgRank = 2)) &
"     ·     Overdue: " & CountRows(Filter(colBuyerRFQs, UrgRank = 0))
```

### 4. `cboBqSort`  ·  **Items**

*Urgent first, then due date* becomes *Most urgent first* and moves to the top of the list.

```powerfx
Table(
    { Value: "Most urgent first" },
    { Value: "Due date, soonest first" },
    { Value: "Due date, latest first" },
    { Value: "Waiting on me first" },
    { Value: "Overdue first" },
    { Value: "Status" },
    { Value: "Requestor name" },
    { Value: "Recently updated" },
    { Value: "RFQ number, newest first" }
)
```

### 5. `cboBqSort`  ·  **DefaultSelectedItems**

The queue now opens already triaged.

```powerfx
Table({ Value: "Most urgent first" })
```

### 6. `galBqQueue`  ·  **Items**

The two urgency-related sorts now use UrgRank, and the fallback matches the new default.

```powerfx
With(
    {
        base: Filter(
            colBuyerRFQs,
            (IsBlank(txtBqSearch.Text)
                || StartsWith(Title, txtBqSearch.Text)
                || txtBqSearch.Text in Description),
            (tglBqShowClosed.Value || !('RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"]))
        )
    },
    Switch(
        Coalesce(cboBqSort.Selected.Value, "Most urgent first"),
        "Due date, soonest first", Sort(base, RFQduedate, SortOrder.Ascending),
        "Due date, latest first", Sort(base, RFQduedate, SortOrder.Descending),
        // Sort is stable, so the inner due-date order survives the outer pass.
        "Waiting on me first",
            Sort(Sort(base, RFQduedate, SortOrder.Ascending), If(AwaitingAction.Value = "Buyer", 0, 1), SortOrder.Ascending),
        "Most urgent first",
            Sort(Sort(base, RFQduedate, SortOrder.Ascending), UrgRank, SortOrder.Ascending),
        "Overdue first",
            Sort(Sort(base, RFQduedate, SortOrder.Ascending), If(UrgRank = 0, 0, 1), SortOrder.Ascending),
        "Status", Sort(Sort(base, RFQduedate, SortOrder.Ascending), 'RFQ status'.Value, SortOrder.Ascending),
        "Requestor name", Sort(base, Coalesce(RequestorName, 'Created By'.DisplayName, ""), SortOrder.Ascending),
        "Recently updated", Sort(base, Modified, SortOrder.Descending),
        "RFQ number, newest first", Sort(base, ID, SortOrder.Descending),
        Sort(base, RFQduedate, SortOrder.Ascending)
    )
)
```

### 7. `lblBqRowUrgency`  ·  **Text**

The urgency cell. This is the change you actually asked for.

```powerfx
Switch(
    ThisItem.UrgRank,
    0, "OVERDUE " & Abs(ThisItem.DaysLeft) & "d",
    1, "DUE TODAY",
    2, "URGENT " & ThisItem.DaysLeft & "d",
    8, "No due date",
    9, "",
    ThisItem.DaysLeft & " days"
)
```

### 8. `lblBqRowUrgency`  ·  **Color**

Red overdue and due-today, amber within 3 days, grey otherwise.

```powerfx
Switch(
    ThisItem.UrgRank,
    0, ColorValue("#A32D2D"),
    1, ColorValue("#A32D2D"),
    2, ColorValue("#854F0B"),
    RGBA(96, 106, 126, 1)
)
```

### 9. `lblBqRowUrgency`  ·  **FontWeight**

**This property is not currently set on the control** — set it from the dropdown at the top of the property pane, then paste. Bolds the rows that are already late.

```powerfx
If(ThisItem.UrgRank <= 1, FontWeight.Semibold, FontWeight.Normal)
```


## scrHome

### 10. Screen `scrHome`  ·  **OnVisible**

Same two fields for the requestor list.

```powerfx
Set(varConfirmAction, Blank());
Set(varShowAlternate, false);
Set(varSaving, false);
Refresh(RFQ);
// Urgency is worked out from the due date each time this loads, so a request
// raised weeks ahead still climbs the list as its due date approaches.
//   0 overdue | 1 due today | 2 due within 3 days | 3 later | 8 no date | 9 closed
ClearCollect(
    colMyRFQs,
    AddColumns(
        AddColumns(
            Filter(RFQ, 'Requestor Email' = User().Email || 'Requestor Email' = varMyMail),
            DaysLeft, If(IsBlank(RFQduedate), 9999, DateDiff(Today(), RFQduedate, TimeUnit.Days))
        ),
        UrgRank,
            If(
                'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], 9,
                IsBlank(RFQduedate), 8,
                DaysLeft < 0, 0,
                DaysLeft = 0, 1,
                DaysLeft <= 3, 2,
                3
            )
    )
);
Reset(txtHmSearch);
Reset(cboHmStatus);
Reset(tglHmAwaitingMe);
Reset(cboHmSort);
Set(varHmDeepGo, false);
If(
    varDeepLinkID > 0 && !IsBlank(LookUp(RFQ, ID = varDeepLinkID)),
    Set(varSelectedRFQ, LookUp(RFQ, ID = varDeepLinkID));
    Set(varChecklist, LookUp(RFQ_Checklist, RFQID = varDeepLinkID));
    Set(varDeepLinkID, 0);
    Set(varHmDeepGo, true)
)
```

### 11. `btnHmRefresh`  ·  **OnSelect**

Same rebuild behind Refresh. Same warning as above.

```powerfx
Refresh(RFQ);
ClearCollect(
    colMyRFQs,
    AddColumns(
        AddColumns(
            Filter(RFQ, 'Requestor Email' = User().Email || 'Requestor Email' = varMyMail),
            DaysLeft, If(IsBlank(RFQduedate), 9999, DateDiff(Today(), RFQduedate, TimeUnit.Days))
        ),
        UrgRank,
            If(
                'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], 9,
                IsBlank(RFQduedate), 8,
                DaysLeft < 0, 0,
                DaysLeft = 0, 1,
                DaysLeft <= 3, 2,
                3
            )
    )
);
Notify("RFQ list refreshed.", NotificationType.Success, 2000)
```

### 12. `lblHmChip3`  ·  **Text**

Fixes the blank-due-date miscount.

```powerfx
"PAST DUE DATE      " & CountRows(Filter(colMyRFQs, UrgRank = 0))
```

### 13. `lblHmRowDue`  ·  **Text**

Puts the word on a second line inside the label you already have, so no new control and no clipping in the 120px column.

```powerfx
Text(ThisItem.RFQduedate, "dd mmm yyyy") &
Switch(ThisItem.UrgRank, 0, Char(10) & "OVERDUE", 1, Char(10) & "DUE TODAY", 2, Char(10) & "URGENT", "")
```

### 14. `lblHmRowDue`  ·  **Color**

Amber threshold moves from 2 days to 3, matching the buyer view.

```powerfx
Switch(
    ThisItem.UrgRank,
    0, ColorValue("#A32D2D"),
    1, ColorValue("#A32D2D"),
    2, ColorValue("#854F0B"),
    9, RGBA(96, 106, 126, 1),
    RGBA(43, 54, 78, 1)
)
```

### 15. `cboHmSort`  ·  **Items**

Adds *Most urgent first*. Home keeps *Waiting on me first* as its default.

```powerfx
Table(
    { Value: "Waiting on me first" },
    { Value: "Most urgent first" },
    { Value: "Due date, soonest first" },
    { Value: "Due date, latest first" },
    { Value: "Recently updated" },
    { Value: "RFQ number, newest first" },
    { Value: "RFQ number, oldest first" },
    { Value: "Status" }
)
```

### 16. `galHmRFQs`  ·  **Items**

Adds the matching sort branch.

```powerfx
With(
    {
        base: Filter(
            colMyRFQs,
            (IsBlank(txtHmSearch.Text)
                || StartsWith(Title, txtHmSearch.Text)
                || txtHmSearch.Text in Description),
            (IsBlank(cboHmStatus.Selected) || 'RFQ status'.Value = cboHmStatus.Selected.Value),
            (!tglHmAwaitingMe.Value || AwaitingAction.Value = "Requestor")
        )
    },
    Switch(
        Coalesce(cboHmSort.Selected.Value, "Waiting on me first"),
        // Sort by due date underneath, then bring the ones that need the
        // requestor to the top. Power Fx Sort is stable, so both hold.
        "Waiting on me first",
            Sort(Sort(base, RFQduedate, SortOrder.Ascending), If(AwaitingAction.Value = "Requestor", 0, 1), SortOrder.Ascending),
        "Most urgent first",
            Sort(Sort(base, RFQduedate, SortOrder.Ascending), UrgRank, SortOrder.Ascending),
        "Due date, soonest first", Sort(base, RFQduedate, SortOrder.Ascending),
        "Due date, latest first", Sort(base, RFQduedate, SortOrder.Descending),
        "Recently updated", Sort(base, Modified, SortOrder.Descending),
        "RFQ number, newest first", Sort(base, ID, SortOrder.Descending),
        "RFQ number, oldest first", Sort(base, ID, SortOrder.Ascending),
        "Status", Sort(Sort(base, RFQduedate, SortOrder.Ascending), 'RFQ status'.Value, SortOrder.Ascending),
        Sort(base, Modified, SortOrder.Descending)
    )
)
```


## scrChecklist

### 17. `lblCkSummary`  ·  **Text**

Header line, live band instead of the frozen choice value.

```powerfx
PlainText(Coalesce(varSelectedRFQ.Description, "")) & Char(10) &
varSelectedRFQ.Quantity & " " & Coalesce(varSelectedRFQ.UOM, "") &
"     ·     Requested by " & varSelectedRFQ.'Requestor Email' &
"     ·     " & With(
    { d: DateDiff(Today(), varSelectedRFQ.RFQduedate, TimeUnit.Days) },
    If(
        varSelectedRFQ.'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], "Closed",
        IsBlank(varSelectedRFQ.RFQduedate), "No due date set",
        d < 0, "OVERDUE by " & Abs(d) & If(Abs(d) = 1, " day", " days"),
        d = 0, "DUE TODAY",
        d <= 3, "URGENT, due in " & d & If(d = 1, " day", " days"),
        "Due in " & d & " days"
    )
) &
"     ·     Due " & Text(varSelectedRFQ.RFQduedate, "dd mmm yyyy") &
"     ·     Sent " & If(IsBlank(varChecklist.RFQSentDate), "not recorded", Text(varChecklist.RFQSentDate, "dd mmm yyyy"))
```


## scrAwardConfirm

### 18. `lblAwSummary`  ·  **Text**

Same.

```powerfx
varSelectedRFQ.Description & Char(10) &
varSelectedRFQ.Quantity & " " & Coalesce(varSelectedRFQ.UOM, "") &
"     ·     " & With(
    { d: DateDiff(Today(), varSelectedRFQ.RFQduedate, TimeUnit.Days) },
    If(
        varSelectedRFQ.'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], "Closed",
        IsBlank(varSelectedRFQ.RFQduedate), "No due date set",
        d < 0, "OVERDUE by " & Abs(d) & If(Abs(d) = 1, " day", " days"),
        d = 0, "DUE TODAY",
        d <= 3, "URGENT, due in " & d & If(d = 1, " day", " days"),
        "Due in " & d & " days"
    )
) &
"     ·     Due " & Text(varSelectedRFQ.RFQduedate, "dd mmm yyyy") &
"     ·     Buyer: " & Coalesce(varSelectedRFQ.'Assigned Buyer', "not assigned")
```


## scrSendRFQ

### 19. `lblSvSummaryBody`  ·  **Text**

Same.

```powerfx
PlainText(Coalesce(varSelectedRFQ.Description, "")) & Char(10) & Char(10) &
"Quantity: " & varSelectedRFQ.Quantity & " " & Coalesce(varSelectedRFQ.UOM, "") & Char(10) &
"Urgency: " & With(
    { d: DateDiff(Today(), varSelectedRFQ.RFQduedate, TimeUnit.Days) },
    If(
        varSelectedRFQ.'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], "Closed",
        IsBlank(varSelectedRFQ.RFQduedate), "No due date set",
        d < 0, "OVERDUE by " & Abs(d) & If(Abs(d) = 1, " day", " days"),
        d = 0, "DUE TODAY",
        d <= 3, "URGENT, due in " & d & If(d = 1, " day", " days"),
        "Due in " & d & " days"
    )
) & Char(10) &
"Due: " & Text(varSelectedRFQ.RFQduedate, "dd mmm yyyy") & Char(10) &
"Raised by: " & Coalesce(varSelectedRFQ.RequestorName, varSelectedRFQ.'Created By'.DisplayName, "Unknown") & Char(10) &
"Contact: " & Coalesce(varSelectedRFQ.'Requestor Email', varSelectedRFQ.'Created By'.Email, "no email on record") & Char(10) & Char(10) &
If(varSelectedRFQ.'Sole Source', "SOLE SOURCE" & Char(10) & PlainText(Coalesce(varSelectedRFQ.'Business Justification', "")) & Char(10) & Char(10), "") &
If(!IsBlank(varSelectedRFQ.'Recommend Vendor') || !IsBlank(varSelectedRFQ.RecVendor2Name) || !IsBlank(varSelectedRFQ.RecVendor3Name), "Requestor suggested " & CountRows(Filter(Table({ N: Coalesce(varSelectedRFQ.'Recommend Vendor', "") }, { N: Coalesce(varSelectedRFQ.RecVendor2Name, "") }, { N: Coalesce(varSelectedRFQ.RecVendor3Name, "") }), !IsBlank(N))) & " vendor(s), see the panel below" & Char(10), "") &
If(!IsBlank(varChecklist.PreferredVendorName), "Requestor asked for: " & varChecklist.PreferredVendorName & Char(10) & PlainText(Coalesce(varChecklist.RequestorJustification, "")), "")
```

### 20. `rtePreview`  ·  **Default**

**The vendor-facing email.** Deliberately says only Urgent or Standard, never OVERDUE — slippage is internal.

This is the long vendor email HTML. Find the one fragment below and change it in place — do **not** repaste the whole thing.

Find:

```powerfx
<br>Urgency: " & Text(varSelectedRFQ.Urgency.Value) & "<br>
```

Replace with:

```powerfx
<br>Urgency: " & If(DateDiff(Today(), varSelectedRFQ.RFQduedate, TimeUnit.Days) <= 3, "Urgent", "Standard") & "<br>
```


## scrEditRFQ

### 21. `btnEdBack`  ·  **OnSelect**

Drops one line from the unsaved-changes test. Without this the screen claims unsaved changes the moment you open an RFQ whose stored value has gone stale.

**Delete one line** from the unsaved-changes test near the top. Nothing replaces it.

Find:

```powerfx
|| radEdUrgency.Selected.Value <> varSelectedRFQ.Urgency.Value
```

Delete that line, including the leading `||`.

### 22. `lblEdLblUrgency`  ·  **Text**

Says where the value comes from.

```powerfx
"Urgency (from due date)"
```

### 23. `radEdUrgency`  ·  **Default**

The radio becomes a read-out of the date picker.

```powerfx
If(DateDiff(Today(), dteEdDueDate.SelectedDate, TimeUnit.Days) <= 3, "Urgent", "Not urgent")
```

### 24. `radEdUrgency`  ·  **DisplayMode**

Read-only, so it can never be set to contradict the due date.

```powerfx
DisplayMode.View
```

### 25. `lblEdProgressBody`  ·  **Text**

Shows the band to everyone. The old `(past due)` was gated on `varCanEdit`, so it vanished once the RFQ went out to vendors — exactly when it mattered.

```powerfx
"Currently waiting on: " & Coalesce(varSelectedRFQ.AwaitingAction.Value, "nobody, this RFQ is finished") &
Char(10) & "Assigned buyer: " & Coalesce(varSelectedRFQ.'Assigned Buyer', "not assigned yet") &
Char(10) & "Raised: " & Text(varSelectedRFQ.'RFQ Raise Date', "dd mmm yyyy") & "     Last updated: " & Text(varSelectedRFQ.Modified, "dd mmm yyyy hh:mm") &
Char(10) & "Due: " & Text(varSelectedRFQ.RFQduedate, "dd mmm yyyy") & "     " & With(
    { d: DateDiff(Today(), varSelectedRFQ.RFQduedate, TimeUnit.Days) },
    If(
        varSelectedRFQ.'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"], "Closed",
        IsBlank(varSelectedRFQ.RFQduedate), "No due date set",
        d < 0, "OVERDUE by " & Abs(d) & If(Abs(d) = 1, " day", " days"),
        d = 0, "DUE TODAY",
        d <= 3, "URGENT, due in " & d & If(d = 1, " day", " days"),
        "Due in " & d & " days"
    )
)
```

### 26. `btnEdSave`  ·  **OnSelect**

One line inside the Patch changes. Find `Urgency: { Value: ... }` and replace that line only — do not repaste the whole formula.

Scroll to the `Patch(RFQ, varSelectedRFQ, {` block, about two thirds down. Change this one line:

Find:

```powerfx
Urgency: { Value: radEdUrgency.Selected.Value },
```

Replace with:

```powerfx
Urgency: { Value: If(DateDiff(Today(), dteEdDueDate.SelectedDate, TimeUnit.Days) <= 3, "Urgent", "Not urgent") },
```

---

## The bands

| Rank | Meaning | Buyer Queue cell | Home due cell |
|---|---|---|---|
| 0 | Past its due date | `OVERDUE 9d`, red, bold | `OVERDUE`, red |
| 1 | Due today | `DUE TODAY`, red, bold | `DUE TODAY`, red |
| 2 | Due within 3 days | `URGENT 2d`, amber | `URGENT`, amber |
| 3 | Due later | `9 days`, grey | date only |
| 8 | No due date recorded | `No due date` | date only |
| 9 | Closed or cancelled | blank | grey |

Three days matches `varNwUrgentDays` on the New RFQ screen, so what a requestor is
told at raise time is what the buyer later sees. To change the threshold, edit the
two `OnVisible` formulas and `varNwUrgentDays` together.

## What to check afterwards

1. Open the Buyer Queue. It should open sorted *Most urgent first*, with anything
   past its date at the top in red.
2. Take an RFQ with a due date more than a week out. In SharePoint, set its due
   date to yesterday. Refresh the queue — it should now read `OVERDUE 1d` and jump
   to the top, **without anyone editing the RFQ**. That single test is the whole
   point of this change.
3. Set another one to today: `DUE TODAY`.
4. Check a closed RFQ with a date in the past shows a blank urgency cell, not red.
5. Open an RFQ in Edit and press Back straight away. It must not claim unsaved
   changes.
6. On Edit, move the due date to tomorrow — the Urgency radio should follow to
   *Urgent* on its own. It is greyed out now; that is intended.
7. Send an RFQ to yourself from a deliberately overdue record and confirm the
   vendor email says `Urgency: Urgent`, never `OVERDUE`.

## Things this does not do

- **Nothing emails anyone when an RFQ goes overdue.** The app can only colour what
  is on screen. Chasing needs a scheduled Power Automate flow over the `RFQ` list.
- **Bands refresh on screen load, not on a clock.** An app left open overnight
  shows yesterday's bands until you navigate or press Refresh.
- **The stored `Urgency` column is still written** on save, now always derived from
  the due date so it cannot contradict the picker. Nothing in the app reads it; it
  is there for SharePoint views and reporting.
