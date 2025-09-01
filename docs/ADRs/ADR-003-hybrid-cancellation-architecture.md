# ADR-003: Hybrid JavaScript + Server-Side Sales Invoice Cancellation Architecture

**Status**: Implemented ⚠️ Pending Tests  
**Date**: 2025-09-01  
**Version**: v2.2.0

## Context

The commission system faced a critical UX problem when users attempted to cancel Sales Invoices that were linked to submitted Orden de Pago Comisiones (OPC) documents. ERPNext's native behavior showed a confusing "Cancel all documents" dialog that could accidentally cancel the entire OPC, destroying valuable commission payment records.

### The Core Problem
ERPNext's native cancellation flow:
1. User clicks Cancel on Sales Invoice
2. ERPNext detects linked documents via Link fields
3. Shows generic "Cancel all documents" dialog
4. User confusion: dialog doesn't explain what "all documents" means
5. Risk: Accidental OPC cancellation destroys commission payment records
6. Business Impact: Loss of audit trail and commission payment history

### Business Requirements
- Prevent accidental OPC cancellation
- Maintain commission payment audit trail
- Enable graceful Sales Invoice cancellations
- Provide clear user guidance during cancellation process
- Automatically handle commission adjustments for future payments

## Decision

We implemented a **Hybrid JavaScript + Server-Side Architecture** that intercepts ERPNext's native cancellation flow and provides a custom business-aware solution.

### Architecture Components

#### 1. Client-Side Interceptor (`sales_invoice_cancel_guard.js`)
**Purpose**: Prevent ERPNext's native dialog from appearing  
**Mechanism**: 
- Hook into ERPNext's `before_cancel` form event
- Execute BEFORE ERPNext analyzes document links
- Show custom business-aware dialog
- Temporarily break OPC link to prevent native "Cancel all documents" detection
- Create backup mechanism for server-side recovery

#### 2. Server-Side Triple Fallback (`commissions.py`)
**Purpose**: Robust OPC detection and adjustment creation  
**Mechanism**:
- **Fallback 1**: Direct field link (`custom_orden_de_pago_comision`)
- **Fallback 2**: JavaScript backup (`__opc_link_backup`)
- **Fallback 3**: Child table search (`Comision LLCS` by `sales_invoice_id`)

#### 3. Automatic Adjustment System (`Ajuste Comision Pendiente`)
**Purpose**: Track and recover cancelled commissions  
**Mechanism**:
- Create negative adjustment records for each cancelled commission
- Anti-duplication logic prevents double-adjustments
- Automatic consumption in next OPC generation
- Status tracking from "Pendiente" to "Aplicado"

#### 4. OPC Protection Hook (`before_opc_cancel`)
**Purpose**: Prevent accidental OPC cancellation  
**Mechanism**:
- Block OPC cancellation if active Sales Invoices are linked
- Provide clear error message with guidance
- Force users through proper SI cancellation workflow

## Alternatives Considered

### 1. Server-Side Only Solution
**Approach**: Use only ERPNext server hooks  
**Rejected Because**:
- Server-side `before_cancel` executes AFTER ERPNext's native dialog detection
- Cannot prevent the confusing "Cancel all documents" dialog
- Poor user experience with technical ERPNext dialogs

### 2. Pure JavaScript Solution  
**Approach**: Handle everything client-side  
**Rejected Because**:
- Cannot guarantee execution if JavaScript is disabled
- Complex business logic better handled server-side
- Frappe framework patterns favor server-side data processing
- Difficult to maintain audit trail and data integrity

### 3. DocType Override Solution
**Approach**: Override Sales Invoice DocType completely  
**Rejected Because**:
- High complexity and maintenance burden
- Breaks ERPNext upgrade compatibility
- Overkill for solving specific cancellation UX issue

### 4. Workflow State Solution
**Approach**: Use ERPNext Workflow to control cancellation  
**Rejected Because**:
- Adds complexity to document lifecycle
- Workflow system not designed for this type of business logic
- Still doesn't solve native dialog UX problem

## Implementation Details

### JavaScript Interceptor Flow
```javascript
frappe.ui.form.on('Sales Invoice', {
  before_cancel(frm) {
    // 1. Check for OPC link
    const opc = frm.doc.custom_orden_de_pago_comision;
    if (!opc) return; // No link, allow native flow
    
    // 2. Show custom dialog
    frappe.confirm("Clear business explanation...", () => {
      // 3. Create backup and break link
      frm.doc.__opc_link_backup = opc;
      frm.doc.custom_orden_de_pago_comision = null;
      
      // 4. Proceed with cancellation (ERPNext sees no links)
      frm.cancel();
    });
    
    // 5. Block native flow
    return false;
  }
});
```

### Server-Side Triple Fallback
```python
def on_sales_invoice_cancel(doc, method):
    # Triple fallback search for robust OPC detection
    opc_name = (
        doc.get("custom_orden_de_pago_comision")           # Fallback 1: Direct link
        or getattr(doc, "__opc_link_backup", None)         # Fallback 2: JS backup
        or _find_opc_by_sales_invoice(doc.name)            # Fallback 3: Child search
    )
    
    if opc_name:
        create_commission_adjustments(doc, opc_name)
```

### Adjustment System Integration
```python
# Automatic adjustment consumption in next OPC
def get_commission_rows(...):
    # ... existing invoice processing ...
    
    # Add pending adjustments automatically
    pending_adjustments = frappe.get_all("Ajuste Comision Pendiente", 
                                       filters={"status": "Pendiente"})
    for adj in pending_adjustments:
        rows.append({
            "total_comision": adj.monto_ajuste,  # Always negative
            "is_adjustment": 1,
            # ... other fields ...
        })
```

## Benefits

### 1. User Experience
- **Clear Communication**: Custom dialog explains exactly what will happen
- **No Confusion**: Eliminates ERPNext's generic "Cancel all documents" dialog
- **Business Context**: Messages use business terminology (commissions, adjustments)
- **Guided Workflow**: Users understand the process and consequences

### 2. Data Integrity
- **No Data Loss**: Original commission payments preserved in OPC
- **Complete Audit Trail**: Track from original payment → cancellation → recovery
- **Atomic Operations**: All database changes committed together
- **Recovery Mechanisms**: Multiple fallback methods ensure robustness

### 3. Business Process
- **Automatic Recovery**: Next OPC generation includes adjustments automatically
- **Policy Integration**: Adjustments exempt from negative commission policy
- **Protection Mechanisms**: Impossible to accidentally cancel OPCs
- **Scalable Solution**: Handles multiple cancellations and complex scenarios

### 4. Technical Benefits
- **Framework Compliance**: Uses standard ERPNext patterns and hooks
- **Maintainable**: Clear separation of concerns between client and server
- **Testable**: Each component can be tested independently
- **Upgrade Safe**: Minimal framework modifications, standard extension patterns

## Risks and Mitigations

### 1. JavaScript Dependency
**Risk**: Solution partially depends on JavaScript execution  
**Mitigation**: 
- Server-side hooks provide fallback protection
- OPC protection hook works regardless of JavaScript
- Core business logic remains server-side

### 2. Timing Edge Cases
**Risk**: Complex interaction between client and server timing  
**Mitigation**:
- Triple fallback search handles all scenarios
- Database transactions ensure atomicity
- Comprehensive backup mechanisms

### 3. User Training
**Risk**: Users must understand new cancellation workflow  
**Mitigation**:
- Clear dialog messages explain process
- Consistent UX across all cancellation scenarios
- Documentation provides operational guidance

### 4. Testing Complexity
**Risk**: Hybrid solution requires both client and server testing  
**Mitigation**:
- Component isolation enables unit testing
- Integration tests cover full workflow
- Verification scripts validate system readiness

## Success Metrics

### Technical Metrics ⚠️ PENDING TESTING
- **Zero OPC Accidents**: No accidental OPC cancellations due to SI cancellation
- **Complete Recovery**: 100% of cancelled commissions recoverable through adjustments
- **UI Consistency**: Custom dialog appears in 100% of applicable cancellation attempts
- **Fallback Reliability**: Triple fallback system successfully finds OPC in all scenarios

### Business Metrics ⚠️ PENDING TESTING  
- **User Satisfaction**: Reduced confusion and support tickets related to cancellation
- **Audit Compliance**: Complete traceability of all commission adjustments
- **Process Efficiency**: Faster cancellation workflow without manual intervention
- **Data Integrity**: Zero orphaned commission records or broken audit trails

## Future Considerations

### Potential Enhancements
1. **Batch Cancellation**: Extend solution to handle multiple SI cancellations
2. **Advanced Analytics**: Reporting on cancellation patterns and adjustment impacts
3. **Policy Extensions**: More sophisticated adjustment policies and rules
4. **Mobile Compatibility**: Ensure dialog and workflow work on mobile ERPNext

### Migration Path
- Current implementation is additive - no breaking changes to existing data
- Future versions could extend adjustment system for more complex scenarios
- Consider workflow integration for enterprise customers with approval processes

## References
- ERPNext Form Events Documentation
- Frappe Framework Hook System
- Commission System Architecture (ADR-001, ADR-002)
- User Experience Research: ERPNext Cancellation Patterns
- Business Requirements: Commission System v2.2 Specification

---

**Note**: This architecture decision represents a significant advancement in the commission system's robustness and user experience. The hybrid approach balances technical complexity with business requirements while maintaining ERPNext framework compatibility.