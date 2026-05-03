package com.auramarket.audit.service;

import com.auramarket.audit.entity.Audit;
import com.auramarket.audit.repository.AuditRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;


@Service
public class AuditService {

    @Autowired
    private AuditRepository auditRepository;

    public List<Audit> getAllAudits() {
        return auditRepository.findAll();
    }

    public Audit createAudit(Audit audit) {
        return auditRepository.save(audit);
    }
}
