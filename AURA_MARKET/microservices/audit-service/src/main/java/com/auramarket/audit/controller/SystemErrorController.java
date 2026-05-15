package com.auramarket.audit.controller;

import com.auramarket.audit.dto.SystemErrorDTO;
import com.auramarket.audit.entity.SystemError;
import com.auramarket.audit.service.SystemErrorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/audits/errors")
public class SystemErrorController {

    @Autowired
    private SystemErrorService errorService;

    @PostMapping
    public ResponseEntity<SystemError> reportError(@RequestBody SystemErrorDTO dto) {
        SystemError saved = errorService.logError(dto);
        return ResponseEntity.ok(saved);
    }

    @GetMapping("/unresolved")
    public ResponseEntity<List<SystemError>> getUnresolved() {
        return ResponseEntity.ok(errorService.getUnresolved());
    }

    @GetMapping("/all")
    public ResponseEntity<List<SystemError>> getAll() {
        return ResponseEntity.ok(errorService.getAllRecent());
    }

    @PutMapping("/{id}/resolve")
    public ResponseEntity<SystemError> resolveError(@PathVariable String id) {
        SystemError resolved = errorService.resolveError(id);
        if (resolved == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(resolved);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        return ResponseEntity.ok(errorService.getStats());
    }
}
