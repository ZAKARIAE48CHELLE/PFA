package com.auramarket.negotiation.repository;

import com.auramarket.negotiation.entity.MessageNegociation;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface MessageNegociationRepository extends JpaRepository<MessageNegociation, UUID> {
    List<MessageNegociation> findByNegociationIdOrderByTimestampAsc(UUID negociationId);

    @org.springframework.transaction.annotation.Transactional
    @org.springframework.data.jpa.repository.Modifying
    void deleteByNegociationId(UUID negociationId);
}
