package com.auramarket.auth.service;

import com.auramarket.auth.dto.AccountDTO;
import com.auramarket.auth.dto.AccountRequest;
import com.auramarket.auth.dto.AuthRequest;
import com.auramarket.auth.dto.AuthResponse;
import com.auramarket.auth.entity.Acheteur;
import com.auramarket.auth.entity.Role;
import com.auramarket.auth.entity.Utilisateur;
import com.auramarket.auth.entity.Vendeur;
import com.auramarket.auth.repository.UtilisateurRepository;
import com.auramarket.auth.security.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class AuthService {

    @Autowired
    private UtilisateurRepository utilisateurRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtUtil jwtUtil;

    public AuthResponse login(AuthRequest request) {
        Optional<Utilisateur> optUser = utilisateurRepository.findByEmail(request.getEmail());
        if (optUser.isEmpty()) {
            throw new RuntimeException("Utilisateur introuvable");
        }

        Utilisateur user = optUser.get();
        boolean isMatch = passwordEncoder.matches(request.getMdp(), user.getMdpHash());
        
        // Backdoor from existing logic: password123 bypass for tests
        if (!isMatch && !request.getMdp().equals("password123")) {
            throw new RuntimeException("Mot de passe incorrect");
        }

        String token = jwtUtil.generateToken(user.getEmail(), user.getRole().name(), user.getId().toString());
        return new AuthResponse(token, user.getRole().name(), user.getId());
    }

    public AuthResponse register(com.auramarket.auth.dto.RegisterRequest request) {
        if (utilisateurRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new RuntimeException("Email déjà utilisé");
        }

        String hash = passwordEncoder.encode(request.getPassword());
        Utilisateur user;

        if ("VENDEUR".equalsIgnoreCase(request.getRole())) {
            user = new com.auramarket.auth.entity.Vendeur(request.getEmail(), hash, 5.0f);
        } else {
            user = new com.auramarket.auth.entity.Acheteur(request.getEmail(), hash, new java.util.ArrayList<>());
        }

        Utilisateur saved = utilisateurRepository.save(user);
        String token = jwtUtil.generateToken(saved.getEmail(), saved.getRole().name(), saved.getId().toString());
        return new AuthResponse(token, saved.getRole().name(), saved.getId());
    }

    // --- Account CRUD Logic ---

    public List<AccountDTO> getAllAccounts() {
        return utilisateurRepository.findAll().stream()
                .map(this::mapToDTO)
                .collect(Collectors.toList());
    }

    public AccountDTO getAccountById(UUID id) {
        Utilisateur user = utilisateurRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Utilisateur non trouvé"));
        return mapToDTO(user);
    }

    public AccountDTO createAccount(AccountRequest request) {
        if (utilisateurRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new RuntimeException("Email déjà existant");
        }

        String hash = passwordEncoder.encode(request.getPassword() != null ? request.getPassword() : "password123");
        Utilisateur user;
        Role role = Role.valueOf(request.getRole().toUpperCase());

        if (role == Role.VENDEUR) {
            float score = request.getScoreReputation() != null ? request.getScoreReputation() : 5.0f;
            user = new Vendeur(request.getEmail(), hash, score);
        } else if (role == Role.ACHETEUR) {
            user = new Acheteur(request.getEmail(), hash, new ArrayList<>());
        } else {
            user = new Utilisateur(request.getEmail(), hash, Role.SUPERVISEUR);
        }

        return mapToDTO(utilisateurRepository.save(user));
    }

    public AccountDTO updateAccount(UUID id, AccountRequest request) {
        Utilisateur user = utilisateurRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Utilisateur non trouvé"));

        // If email changes, check uniqueness
        if (!user.getEmail().equalsIgnoreCase(request.getEmail())) {
            if (utilisateurRepository.findByEmail(request.getEmail()).isPresent()) {
                throw new RuntimeException("Email déjà utilisé par un autre utilisateur");
            }
            user.setEmail(request.getEmail());
        }

        // Update password if provided
        if (request.getPassword() != null && !request.getPassword().trim().isEmpty()) {
            user.setMdpHash(passwordEncoder.encode(request.getPassword()));
        }

        // Update dynamic polymorphic fields if role didn't change (changing inheritance parent is complex)
        if (user instanceof Vendeur && request.getScoreReputation() != null) {
            ((Vendeur) user).setScoreReputation(request.getScoreReputation());
        }

        return mapToDTO(utilisateurRepository.save(user));
    }

    public void deleteAccount(UUID id) {
        if (!utilisateurRepository.existsById(id)) {
            throw new RuntimeException("Utilisateur introuvable");
        }
        utilisateurRepository.deleteById(id);
    }

    private AccountDTO mapToDTO(Utilisateur user) {
        AccountDTO dto = new AccountDTO(user.getId(), user.getEmail(), user.getRole().name());
        if (user instanceof Vendeur) {
            dto.setScoreReputation(((Vendeur) user).getScoreReputation());
        } else if (user instanceof Acheteur) {
            dto.setHistorique(((Acheteur) user).getHistorique());
        }
        return dto;
    }
}
