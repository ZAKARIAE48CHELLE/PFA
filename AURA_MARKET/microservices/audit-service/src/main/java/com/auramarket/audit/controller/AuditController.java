package com.auramarket.audit.controller;

import com.auramarket.audit.entity.Audit;
import com.auramarket.audit.service.AuditService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/audits")
public class AuditController {

    @Autowired
    private AuditService auditService;

    @GetMapping
    public ResponseEntity<List<Audit>> getAllAudits() {
        return ResponseEntity.ok(auditService.getAllAudits());
    }

    @PostMapping
    public ResponseEntity<Audit> createAudit(@RequestBody Audit audit) {
        return ResponseEntity.ok(auditService.createAudit(audit));
    }
}
