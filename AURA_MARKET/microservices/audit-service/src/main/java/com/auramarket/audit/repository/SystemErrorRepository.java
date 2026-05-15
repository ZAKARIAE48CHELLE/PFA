package com.auramarket.audit.repository;

import com.auramarket.audit.entity.SystemError;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface SystemErrorRepository extends JpaRepository<SystemError, String> {

    List<SystemError> findByOrderByCreatedAtDesc();

    List<SystemError> findByResolvedFalseOrderByCreatedAtDesc();

    long countByResolvedFalse();

    long countBySeverityAndResolvedFalse(String severity);

    @Modifying
    @Query("DELETE FROM SystemError e WHERE e.createdAt < :cutoff AND e.resolved = true")
    int deleteByCreatedAtBeforeAndResolvedTrue(@Param("cutoff") LocalDateTime cutoff);
}
