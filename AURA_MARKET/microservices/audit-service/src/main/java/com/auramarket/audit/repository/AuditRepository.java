package com.auramarket.audit.repository;

import com.auramarket.audit.entity.Audit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface AuditRepository extends JpaRepository<Audit, UUID> {
}
