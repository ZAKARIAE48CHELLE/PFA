package com.auramarket.audit.service;

import com.auramarket.audit.dto.SystemErrorDTO;
import com.auramarket.audit.entity.SystemError;
import com.auramarket.audit.repository.SystemErrorRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class SystemErrorService {

    @Autowired
    private SystemErrorRepository repo;

    @Autowired
    private ErrorNotificationService notifier;

    @Transactional
    public SystemError logError(SystemErrorDTO dto) {
        SystemError err = new SystemError();
        err.setService(dto.getService() != null ? dto.getService() : "unknown");
        err.setErrorType(dto.getErrorType() != null ? dto.getErrorType() : "UNKNOWN_ERROR");
        
        // Truncate massive message strings to prevent overflow
        String msg = dto.getMessage() != null ? dto.getMessage() : "No details";
        if (msg.length() > 990) msg = msg.substring(0, 990) + "...";
        err.setMessage(msg);

        err.setStackTrace(dto.getStackTrace());
        err.setNegociationId(dto.getNegociationId());
        err.setUserId(dto.getUserId());
        err.setProduitId(dto.getProduitId());
        err.setAgentName(dto.getAgentName());
        
        String sev = dto.getSeverity() != null ? dto.getSeverity().toUpperCase() : deriveSeverity(dto.getErrorType());
        err.setSeverity(sev);
        err.setDurationMs(dto.getDurationMs());
        err.setPayload(dto.getPayload());
        err.setEndpoint(dto.getEndpoint());

        SystemError saved = repo.save(err);
        System.out.println("[DB SAVE] Logged error ID: " + saved.getId() + " Severity: " + sev);

        // Broadcast realtime if critical/high
        notifier.notifySuperviseur(saved);

        return saved;
    }

    public List<SystemError> getUnresolved() {
        return repo.findByResolvedFalseOrderByCreatedAtDesc();
    }

    public List<SystemError> getAllRecent() {
        return repo.findByOrderByCreatedAtDesc();
    }

    @Transactional
    public SystemError resolveError(String id) {
        SystemError err = repo.findById(id).orElse(null);
        if (err != null) {
            err.setResolved(true);
            return repo.save(err);
        }
        return null;
    }

    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalUnresolved", repo.countByResolvedFalse());
        stats.put("criticalUnresolved", repo.countBySeverityAndResolvedFalse("CRITICAL"));
        stats.put("highUnresolved", repo.countBySeverityAndResolvedFalse("HIGH"));
        stats.put("mediumUnresolved", repo.countBySeverityAndResolvedFalse("MEDIUM"));
        stats.put("lowUnresolved", repo.countBySeverityAndResolvedFalse("LOW"));
        return stats;
    }

    @Transactional
    @Scheduled(cron = "0 0 2 * * *") // Every night at 2:00 AM
    public void purgeOldErrors() {
        LocalDateTime cutoff = LocalDateTime.now().minusDays(30);
        int deleted = repo.deleteByCreatedAtBeforeAndResolvedTrue(cutoff);
        System.out.println("[ErrorPurge] Nightly maintenance: Purged " + deleted + " resolved historical failures (>30 days).");
    }

    private String deriveSeverity(String errorType) {
        if (errorType == null) return "MEDIUM";
        return switch (errorType.toUpperCase()) {
            case "TIMEOUT", "DB_ERROR" -> "CRITICAL";
            case "LLM_ERROR", "JADE_ERROR", "NEGO_ERROR" -> "HIGH";
            case "INVALID_CONFIG", "AUTH_ERROR" -> "MEDIUM";
            default -> "LOW";
        };
    }
}
