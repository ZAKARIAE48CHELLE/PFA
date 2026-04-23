package com.auramarket.negotiation.repository;

import com.auramarket.negotiation.entity.Negociation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface NegociationRepository extends JpaRepository<Negociation, UUID> {
}
