# Deploying this branch into Power Apps Studio

Written for the **paste-controls-in-Studio** route. Screen-level properties do
not travel with a control paste, so those are reproduced in full below.

Work top to bottom. Everything in Part 1 must be true before you paste a single
control, otherwise Studio fills with red that tells you nothing.

---

## Part 1 — before you paste anything

| # | Do this | Why |
|---|---|---|
| 1 | Note the current version under **Settings -> Versions** | Your rollback point. Eight screens is too much to unwind by hand. |
| 2 | Create **`SendRFQNotification`** and add it to the app | 7 call sites across 4 screens. Until the flow is added, every one fails to resolve. |
| 3 | Confirm your 7-input flow is named **`SendRFQToVendors`** | The send screen calls that name. Rename it in Power Automate if it is still called `sendRFQNotification`. |
| 4 | **Data pane -> RFQ -> Refresh** | Publishes the seven new `RecVendor*` columns to the app. |
| 5 | Confirm **`Emailcontact`** resolves on `SG Vendor Master List` | Six vendor pickers read it. A different display name breaks all six at once. |
| 6 | Set **`App.OnStart`** (see Part 4) | Nothing in these screens creates `varRole` or `varDeepLinkID`. Without it everyone is a Requestor. |

---

## Part 2 — paste order, screen by screen

**The trap:** pasting a control whose name already exists on the screen makes
Studio rename it `btnSvBack_1`, and every formula that referenced the original
keeps pointing at the old one. So for any screen you re-paste: **select all the
existing controls on that screen and delete them first**, then paste.

Paste the `Children:` list in file order. Later entries sit on top, which is what
keeps the confirm dialogs and the send preview above the rest of the screen.

| Screen | Changed lines | Action | OnVisible |
|---|---|---|---|
| `scrAdminUsers` | 18 | Hand-edit the few formulas (see Part 3) | unchanged |
| `scrAwardConfirm` | 71 | Hand-edit the few formulas (see Part 3) | unchanged |
| `scrBuyerQueue` | 83 | Hand-edit the few formulas (see Part 3) | **Yes — repaste it** |
| `scrChecklist` | 333 | Full re-paste | unchanged |
| `scrEditRFQ` | 539 | Full re-paste | **Yes — repaste it** |
| `scrHome` | 87 | Hand-edit the few formulas (see Part 3) | **Yes — repaste it** |
| `scrNewRFQ` | 520 | Full re-paste | **Yes — repaste it** |
| `scrSendRFQ` | 576 | Full re-paste | **Yes — repaste it** |

Order does not matter between screens, only within one. Publish once at the end.

---

## Part 3 — the light-touch screens

`scrAdminUsers`, `scrAwardConfirm` and `scrBuyerQueue` changed too little to be
worth clearing and re-pasting. Open each formula and edit in place:

### scrAdminUsers

- **Every comparison against the `Role` column** — `Role = "Admin"` becomes `Trim(Lower(Role)) = "admin"` (and the same for `"buyer"`). Six places: the two last-admin guards, the header counts, the row colour Switch, and the picker's DefaultSelectedItems. `Role` is free text, so a row typed straight into SharePoint as `admin` would otherwise not count — which let the final administrator be removed.

### scrAwardConfirm

- **`btnAwSubmitAlt.OnSelect` and `btnAwModalYes.OnSelect`** — Both gained a `SendRFQNotification.Run(...)` block so the buyer is told the requestor answered. Copy each OnSelect wholesale from the file.
- **Column names** — `'RFQ  due date'` -> `RFQduedate`, `'ActivityLog '` -> `ActivityLog`, `'ReRFQCount '` -> `ReRFQCount`.

### scrBuyerQueue

- **Screen `OnVisible`** — Adds `Reset(cboBqSort)`. Repaste from Part 4.
- **`galBqQueue.Items`** — Wrapped in `With()` + `Switch()` for the sort picker.
- **New control `cboBqSort`** — Paste just this one control, then set the gallery Items.
- **Column names** — `'RFQ  due date'` -> `RFQduedate` in four places.

---

## Part 4 — screen properties to paste by hand

Select the screen in the tree, pick the property in the formula bar, paste.

### App.OnStart

```powerfx
Set(
    varRole,
    Switch(
        Trim(Lower(Coalesce(LookUp('PWS_SHQ Purchase Requisition SU', Lower(ThisRecord.User.Email) = Lower(User().Email)).Role, ""))),
        "admin", "Admin",
        "buyer", "Buyer",
        "Requestor"
    )
);
Set(varDeepLinkID, Value(Coalesce(Param("rfq"), "0")));
Set(varSaving, false);
Set(varConfirmAction, Blank());
Set(varShowAlternate, false);
```

### scrBuyerQueue.OnVisible

```powerfx
Set(varBqDenied, false);
Set(varBqDenied, varRole <> "Buyer" && varRole <> "Admin");
If(
    varBqDenied,
    Notify("Buyer access only. Taking you back to the home screen.", NotificationType.Error, 4000),
    Refresh(RFQ);
    ClearCollect(colBuyerRFQs, RFQ);
    Set(varConfirmAction, Blank());
    Set(varSaving, false);
    Reset(txtBqSearch);
    Reset(tglBqShowClosed);
    Reset(cboBqSort)
)
```

### scrEditRFQ.OnVisible

```powerfx
Set(varSelectedRFQ, LookUp(RFQ, ID = varSelectedRFQ.ID));
Set(varChecklist, LookUp(RFQ_Checklist, RFQID = varSelectedRFQ.ID));
Set(varCanEdit, !(varSelectedRFQ.'RFQ status'.Value in ["RFQ closed/completed", "RFQ cancelled"]));
Set(varShowHistory, false);
Set(varShowDocs, false);
ClearCollect(colEdDocs, ForAll(varSelectedRFQ.Attachments As Att, { FileName: Att.DisplayName, FileLink: Att.Value }));
Set(varConfirmAction, Blank());
Set(varSaving, false);
ClearCollect(
    colVendorList,
    ForAll(
        'SG Vendor Master List',
        { VendorName: field_2, VendorEmail: Coalesce(Emailcontact, "") }
    )
);
Set(varEdRec1Name, Coalesce(varSelectedRFQ.'Recommend Vendor', ""));
Set(varEdRec1Email, Coalesce(varSelectedRFQ.RecommendVendorEmail, ""));
Set(varEdRec1Manual, !IsBlank(varEdRec1Name) && CountRows(Filter(colVendorList, VendorName = varEdRec1Name)) = 0);
Set(varEdRec2Name, Coalesce(varSelectedRFQ.RecVendor2Name, ""));
Set(varEdRec2Email, Coalesce(varSelectedRFQ.RecVendor2Email, ""));
Set(varEdRec2Manual, !IsBlank(varEdRec2Name) && CountRows(Filter(colVendorList, VendorName = varEdRec2Name)) = 0);
Set(varEdRec3Name, Coalesce(varSelectedRFQ.RecVendor3Name, ""));
Set(varEdRec3Email, Coalesce(varSelectedRFQ.RecVendor3Email, ""));
Set(varEdRec3Manual, !IsBlank(varEdRec3Name) && CountRows(Filter(colVendorList, VendorName = varEdRec3Name)) = 0);
Reset(txtEdDescription);
Reset(txtEdQuantity);
Reset(txtEdUOM);
Reset(radEdUrgency);
Reset(dteEdDueDate);
Reset(tglEdSoleSource);
Reset(txtEdJustification);
Reset(tglEdRec1Manual); Reset(cboEdRec1); Reset(txtEdRec1Name); Reset(txtEdRec1Email); Reset(txtEdRec1Remarks);
Reset(tglEdRec2Manual); Reset(cboEdRec2); Reset(txtEdRec2Name); Reset(txtEdRec2Email); Reset(txtEdRec2Remarks);
Reset(tglEdRec3Manual); Reset(cboEdRec3); Reset(txtEdRec3Name); Reset(txtEdRec3Email); Reset(txtEdRec3Remarks);
Reset(txtEdRemarks)
```

### scrHome.OnVisible

```powerfx
Set(varConfirmAction, Blank());
Set(varShowAlternate, false);
Set(varSaving, false);
Refresh(RFQ);
ClearCollect(colMyRFQs, Filter(RFQ, 'Requestor Email' = User().Email));
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

### scrNewRFQ.OnVisible

```powerfx
UpdateContext({ varShowLabelInstructions: false });
Set(varSaving, false);
Set(varNwUrgentDays, 3);
Set(varNwNormalDays, 7);
Set(varNwUrgency, "Not urgent");
Set(varNwDueDate, Today() + varNwNormalDays);
// Same vendor master the buyer sees, so a suggestion arrives with an address
// already attached instead of the buyer retyping it.
ClearCollect(
    colVendorList,
    ForAll(
        'SG Vendor Master List',
        { VendorName: field_2, VendorEmail: Coalesce(Emailcontact, "") }
    )
);
Set(varNwRec1Name, ""); Set(varNwRec1Email, ""); Set(varNwRec1Manual, false);
Set(varNwRec2Name, ""); Set(varNwRec2Email, ""); Set(varNwRec2Manual, false);
Set(varNwRec3Name, ""); Set(varNwRec3Email, ""); Set(varNwRec3Manual, false);
Reset(txtNwDescription); Reset(txtNwQuantity); Reset(txtNwUOM);
Reset(radNwUrgency); Reset(dteNwDueDate); Reset(tglNwSoleSource); Reset(txtNwJustification);
Reset(tglNwRec1Manual); Reset(cboNwRec1); Reset(txtNwRec1Name); Reset(txtNwRec1Email); Reset(txtNwRec1Remarks);
Reset(tglNwRec2Manual); Reset(cboNwRec2); Reset(txtNwRec2Name); Reset(txtNwRec2Email); Reset(txtNwRec2Remarks);
Reset(tglNwRec3Manual); Reset(cboNwRec3); Reset(txtNwRec3Name); Reset(txtNwRec3Email); Reset(txtNwRec3Remarks);
Reset(txtNwRemarks)
```

### scrSendRFQ.OnVisible

```powerfx
Set(varSelectedRFQ, LookUp(RFQ, ID = varSelectedRFQ.ID));
Set(varChecklist, LookUp(RFQ_Checklist, RFQID = varSelectedRFQ.ID));
// One vendor row can carry several addresses in Emailcontact, written as
// "john@x.com; pete@y.com". They stay one string all the way to the flow,
// which puts the whole lot on BCC.
ClearCollect(
    colVendorList,
    ForAll(
        'SG Vendor Master List',
        { VendorName: field_2, VendorEmail: Coalesce(Emailcontact, "") }
    )
);
Set(varSvV1Name, Coalesce(varChecklist.Vendor1Name, ""));
Set(varSvV2Name, Coalesce(varChecklist.Vendor2Name, ""));
Set(varSvV3Name, Coalesce(varChecklist.Vendor3Name, ""));
Set(varSvV4Name, Coalesce(varChecklist.Vendor4Name, ""));
Set(varSvV1Email, Coalesce(varChecklist.Vendor1Email, ""));
Set(varSvV2Email, Coalesce(varChecklist.Vendor2Email, ""));
Set(varSvV3Email, Coalesce(varChecklist.Vendor3Email, ""));
Set(varSvV4Email, Coalesce(varChecklist.Vendor4Email, ""));
Set(varSvV1Manual, !IsBlank(varSvV1Name) && CountRows(Filter(colVendorList, VendorName = varSvV1Name)) = 0);
Set(varSvV2Manual, !IsBlank(varSvV2Name) && CountRows(Filter(colVendorList, VendorName = varSvV2Name)) = 0);
Set(varSvV3Manual, !IsBlank(varSvV3Name) && CountRows(Filter(colVendorList, VendorName = varSvV3Name)) = 0);
Set(varSvV4Manual, !IsBlank(varSvV4Name) && CountRows(Filter(colVendorList, VendorName = varSvV4Name)) = 0);
Set(varSaving, false);
Set(varShowPreview, false);
Set(varSvConfirmLeave, false);
// Requestor files stay as attachments on the RFQ list item. Sensitivity is
// carried by the real Purview label the requestor applied before uploading,
// not by a column in this app.
ClearCollect(
    colSvDocs,
    ForAll(varSelectedRFQ.Attachments As Att, { FileName: Att.DisplayName, FileLink: Att.Value })
);
Reset(tglSvV1Manual); Reset(cboSvV1); Reset(txtSvV1Name); Reset(txtSvV1Email);
Reset(tglSvV2Manual); Reset(cboSvV2); Reset(txtSvV2Name); Reset(txtSvV2Email);
Reset(tglSvV3Manual); Reset(cboSvV3); Reset(txtSvV3Name); Reset(txtSvV3Email);
Reset(tglSvV4Manual); Reset(cboSvV4); Reset(txtSvV4Name); Reset(txtSvV4Email);
Reset(dteSvSentDate)
```

---

## Part 5 — after pasting

Expect **blue delegation warnings** on `Trim(Lower(Role))` over the access list
and on `ForAll` over the vendor master. Both are deliberate: those lists hold a
handful of rows, far below the limit. Do not rewrite them to plain equality —
that is what reintroduces the role-casing bug.

Red errors are real. The most likely causes, in order:

1. `SendRFQNotification` not added to the app (7 sites light up at once)
2. `RFQ` not refreshed after adding the columns (`RecVendor*` unresolved)
3. `Emailcontact` named differently on the vendor master (6 pickers at once)
4. A control renamed to `_1` because the old one was not deleted first

### Smoke test

| # | Do | Expect |
|---|---|---|
| 1 | Raise an RFQ with 3 suggestions: one from the picker, one via **Not on the list?**, one blank | Every Buyer/Admin gets an email listing both vendors with emails and remarks |
| 2 | Buyer Queue -> open it | Suggestions panel lists exactly the two filled slots |
| 3 | **Use this** on a suggestion | Lands in Vendor 1 with its address, marked as manual entry |
| 4 | Save vendor list -> Review and send -> close the preview **without** sending | Status stays *RFQ pending*. This is the bug that used to mark it sent |
| 5 | Send for real | Vendors on BCC, requestor on CC, attachments present, status now *RFQ sent out* |
| 6 | Checklist: enter quotes, press Back without saving | Returns with a *Quotes kept as a draft* toast, figures intact |
| 7 | Recommend a vendor with no price | Refused, naming the vendor |
| 8 | Recommend properly | Requestor gets the email |
| 9 | Requestor accepts | Buyer gets the email, RFQ closes |
| 10 | Open an RFQ raised before this change | Old title format and single suggested vendor still display |
