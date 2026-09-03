# Deploying this branch into Power Apps Studio

Route: **paste every screen**, rather than hand-editing the lightly changed ones.
More paste work, but every screen ends up matching the repo exactly, so there is
no question later about which formulas were updated and which were missed.

Tenant is **GCC High** (`apps.high.powerapps.us`). Nothing here needs a preview
feature: every control reuses a type and version already in your app, and the
formulas use only long-standing functions.

---

## Part 1 — before you paste anything

| # | Do this | Why |
|---|---|---|
| 1 | Note the current version under **Settings -> Versions** | Your rollback point. |
| 2 | Create **`SendRFQNotification`** and add it to the app | 7 call sites across 4 screens. Until the flow is added every one fails to resolve. |
| 3 | Confirm your 7-input flow is named **`SendRFQToVendors`** | The send screen calls that name. |
| 4 | **Data pane -> RFQ -> Refresh** | Publishes the seven new `RecVendor*` columns. |
| 5 | Confirm **`Emailcontact`** resolves on `SG Vendor Master List` | Six vendor pickers read it. |
| 6 | Set **`App.OnStart`** (Part 4) | Nothing in these screens creates `varRole` or `varDeepLinkID`. |
| 7 | Prove paste works on a **blank throwaway screen** first | Two minutes. Do not clear a real screen until you have seen a paste land. |

---

## Part 2 — the two things that bite

**Clear each screen before pasting into it.** Pasting a control whose name already
exists makes Studio rename the new one `btnSvBack_1`, while every formula keeps
pointing at the old control. The screen looks right and behaves wrong. Select all
controls in the tree for that screen, delete, then paste.

Safe to do: all 489 controls were checked and **no control is referenced from
another screen**, so clearing one screen cannot break a different one.

**Screen properties do not travel with a control paste.** Every screen below needs
its `OnVisible` (and `Fill` / `LoadingSpinnerColor`) set by hand from Part 4.

Paste the `Children:` list in file order — later entries sit on top, which is what
keeps the confirm dialogs and the send preview above the rest of the screen.

---

## Part 3 — screens, in a sensible order

Order between screens does not matter. This one front-loads the small screens so
you confirm the workflow on something cheap before the 100-control screen.

| Order | Screen | Controls | Notes |
|---|---|---|---|
| 1 | `scrBuyerQueue` | 21 | Start here. Smallest. New `cboBqSort`; gallery Items now wrapped in With/Switch. |
| 2 | `scrAwardConfirm` | 33 | Two OnSelect blocks now call `SendRFQNotification`. |
| 3 | `scrAdminUsers` | 36 | Only the `Role` comparisons changed, but paste it whole for consistency. |
| 4 | `scrHome` | 36 | New `cboHmSort`; filter row re-laid out; two galleries to verify. |
| 5 | `scrNewRFQ` | 68 | Card C rebuilt: 3 vendor pickers + toggles. **Check `frmNwAttach` and its attachment card after paste.** |
| 6 | `scrChecklist` | 74 | New read-only suggestions panel; footer moved right. |
| 7 | `scrEditRFQ` | 84 | Form card re-flowed; 3 pickers. **Check `frmEdAttach`.** |
| 8 | `scrSendRFQ` | 100 | Largest. New suggestions panel + leave-confirm dialog. **Check `rtePreview` keeps its Default.** |

### Verify these by hand after their screen is pasted

Composite controls are the ones most likely to come across incomplete:

| Control | Screen | Check |
|---|---|---|
| `frmNwAttach` | scrNewRFQ | `DataSource` is `RFQ`, `Item` is `Defaults(RFQ)`, and the attachment card still has `DataField: "{Attachments}"` |
| `frmEdAttach` | scrEditRFQ | Same, with `Item` bound to the selected RFQ |
| `rtePreview` | scrSendRFQ | The long HTML `Default` survived — this is the vendor letter |
| `htmNwLabelSteps` | scrNewRFQ | `HtmlText` still populated |
| `galHmRFQs`, `galHmAttention` | scrHome | `Items` and the `OnSelect` on each |
| `galBqQueue` | scrBuyerQueue | `Items` (With/Switch sort) and `OnSelect` |
| `galSvDocs` | scrSendRFQ | `Items` bound to `colSvDocs` |
| `galAuUsers` | scrAdminUsers | `Items` and `OnSelect` |

Also confirm the four `Image1_*` controls still point at the `image` media
resource. Media lives at app level, so it survives, but the binding is worth a look.

---

## Part 4 — every screen property, to paste by hand

Select the screen in the tree, choose the property in the formula bar, paste.

### App.OnStart

```powerfx
// This tenant signs users in with an employee-ID UPN (E40124966@adxuser.com),
// not a mailbox, so the sign-in identity and the address people actually email
// are different strings. Keep both in their natural case: a delegated SharePoint
// filter compares case-insensitively server side, Power Fx "=" locally does not.
Set(varMyUpn, User().Email);
Set(varMyMail, Coalesce(Office365Users.MyProfileV2().mail, User().Email));

// Match the access list four ways, cheapest and most reliable first:
//   1. LoginEmail, a plain text column holding the sign-in UPN. Deterministic,
//      needs no connector, and is what Manage Access now fills in on every grant.
//   2/3. the person column's mailbox against either identity.
//   4. the login name inside the person column's Claims.
// Lower() on both sides throughout because this comparison runs locally.
Set(
    varRole,
    Switch(
        Trim(
            Lower(
                Coalesce(
                    LookUp(
                        'PWS_SHQ Purchase Requisition SU',
                        (!IsBlank(ThisRecord.LoginEmail) && Lower(ThisRecord.LoginEmail) = Lower(varMyUpn))
                            || Lower(ThisRecord.User.Email) = Lower(varMyMail)
                            || Lower(ThisRecord.User.Email) = Lower(varMyUpn)
                            || Lower(varMyUpn) in Lower(Coalesce(ThisRecord.User.Claims, ""))
                    ).Role,
                    ""
                )
            )
        ),
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

### scrBuyerQueue

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

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

### scrAwardConfirm

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

```powerfx
Set(varSelectedRFQ, LookUp(RFQ, ID = varSelectedRFQ.ID));
Set(varChecklist, LookUp(RFQ_Checklist, RFQID = varSelectedRFQ.ID));
Set(varShowAlternate, false);
Set(varAwardConfirm, Blank());
Set(varSaving, false);
Reset(txtAwPreferredVendor);
Reset(txtAwAlternateJust)
```

### scrAdminUsers

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

```powerfx
Set(varAuDenied, false);
Set(varAuDenied, Coalesce(varRole, "Requestor") <> "Admin");
If(
    varAuDenied,
    Notify("Only an administrator can change who has access. Taking you back to the home screen.", NotificationType.Error, 4000),
    Refresh('PWS_SHQ Purchase Requisition SU');
    ClearCollect(colAppUsers, 'PWS_SHQ Purchase Requisition SU');
    Set(varAuSelected, Blank());
    Set(varAuConfirmDelete, false);
    Set(varSaving, false);
    Reset(txtAuSearch);
    Reset(txtAuEmail);
    Reset(txtAuName);
    Reset(cboAuRole)
)
```

### scrHome

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

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

### scrNewRFQ

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

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

### scrChecklist

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

```powerfx
Set(varSelectedRFQ, LookUp(RFQ, ID = varSelectedRFQ.ID));
Set(varChecklist, LookUp(RFQ_Checklist, RFQID = varSelectedRFQ.ID));
Set(varCheapestVendor, Blank());
Set(varSaving, false);
Reset(cboCkV1Cur); Reset(txtCkV1Unit); Reset(txtCkV1Total); Reset(txtCkV1Lead);
Reset(cboCkV2Cur); Reset(txtCkV2Unit); Reset(txtCkV2Total); Reset(txtCkV2Lead);
Reset(cboCkV3Cur); Reset(txtCkV3Unit); Reset(txtCkV3Total); Reset(txtCkV3Lead);
Reset(cboCkV4Cur); Reset(txtCkV4Unit); Reset(txtCkV4Total); Reset(txtCkV4Lead);
Reset(cboCkV1Resp); Reset(cboCkV2Resp); Reset(cboCkV3Resp); Reset(cboCkV4Resp);
Reset(cboCkAward); Reset(txtCkNotes)
```

### scrEditRFQ

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

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

### scrSendRFQ

`Fill` = `RGBA(238, 242, 248, 1)`  
`LoadingSpinnerColor` = `RGBA(56, 96, 178, 1)`  

`OnVisible`:

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

**Expected, deliberate, leave alone:** blue delegation warnings on
`Trim(Lower(Role))` over the access list and `ForAll` over the vendor master.
Both lists hold a handful of rows. Rewriting them to plain equality is what
reintroduces the role-casing bug.

**Red errors are real.** Most likely causes, in order:

1. `SendRFQNotification` not added to the app — about 7 sites light up at once
2. `RFQ` not refreshed — every `RecVendor*` unresolved
3. `Emailcontact` named differently on the vendor master — 6 pickers at once
4. A control renamed `_1` because the screen was not cleared first
5. A screen property left unset — usually shows as a blank screen on open

### Smoke test

| # | Do | Expect |
|---|---|---|
| 1 | Sign in as a Buyer | Buyer Queue button visible on Home. If not, `App.OnStart` or the `Role` value |
| 2 | Raise an RFQ with 3 suggestions: one from the picker, one via **Not on the list?**, one blank | Picker fills the email itself; buyers get an email listing both vendors |
| 3 | Buyer Queue -> open it | Suggestions panel shows exactly the two filled slots |
| 4 | **Use this** on a suggestion | Lands in Vendor 1 with its address, flagged as manual entry |
| 5 | Save vendor list -> Review and send -> **close without sending** | Status stays *RFQ pending*. This is the bug that used to mark it sent |
| 6 | Send for real | Vendors on BCC, requestor on CC, **attachments present**, status now *RFQ sent out* |
| 7 | Checklist: type quotes, press Back without saving | Returns with *Quotes kept as a draft*, figures intact |
| 8 | Recommend a vendor with no price | Refused, naming the vendor |
| 9 | Recommend properly | Requestor gets the email |
| 10 | Requestor accepts | Buyer gets the email, RFQ closes |
| 11 | Open an RFQ raised before this change | Old title format and single suggested vendor still display |

Step 6's attachment check is the one that catches the Power Automate gap: if the
vendor email arrives without the requestor's drawings, the flow still needs
`GetAttachments` wiring (see the README).
