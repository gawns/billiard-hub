(function () {
  "use strict";

  // ====== Inisialisasi WOW.js (Animasi saat scroll) ======
  if (typeof WOW === 'function') {
    new WOW().init();
  }

  // ====== Sticky Header ======
  window.onscroll = function () {
    const ud_header = document.querySelector(".ud-header");
    
    if (ud_header) {
      // Sticky setelah scroll 50px
      if (window.pageYOffset > 50) { 
        ud_header.classList.add("sticky");
      } else {
        ud_header.classList.remove("sticky");
      }
    }

    // ====== Tombol Back to Top ======
    const backToTop = document.querySelector(".back-to-top");
    if (backToTop) {
      if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
        backToTop.style.display = "block";
      } else {
        backToTop.style.display = "none";
      }
    }
  };

  // ====== Smooth Scroll (Membutuhkan jQuery) ======
  if (typeof $ === 'function') {
    
    // (DIRALAT) Menambahkan .about-scroll-btn
    $('a.nav-link[href*="#"], a.back-to-top[href*="#"], .hero-buttons a[href*="#"], .about-scroll-btn[href*="#"]').on('click', function (e) {
      const hash = this.hash;
      const $target = $(hash);

      // Pastikan target ada di halaman
      if (hash && hash.length > 1 && $target.length) {
        e.preventDefault();
        
        // (DIRALAT) Gunakan nilai tetap agar akurat
        const navbarHeight = 66; // 65px tinggi header + 1px buffer
        
        let targetOffset = $target.offset().top;

        // Jika target BUKAN #home, kurangi tinggi navbar
        if (hash !== '#home') {
             targetOffset -= navbarHeight;
        } else {
            // Jika target #home, scroll ke paling atas
            targetOffset = 0;
        }

        $('html, body').animate({
          scrollTop: targetOffset
        }, 600, 'swing', function () {
          // Update link aktif di navigasi
          $('a.nav-link').removeClass('active');
          $('a.nav-link[href*="' + hash + '"]').addClass('active');
        });
      }
    });
  }


  // ====== Mobile Menu (Toggler) ======
  const toggler = document.querySelector(".navbar-toggler");
  const navMenu = document.querySelector(".navbar-nav");

  if (toggler && navMenu) {
    toggler.addEventListener("click", () => {
      toggler.classList.toggle("active");
      navMenu.classList.toggle("show");
    });

    // Tutup menu saat link diklik
    const navLinks = document.querySelectorAll(".navbar-nav .nav-link");
    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        if (toggler.classList.contains("active")) {
          toggler.classList.remove("active");
          navMenu.classList.remove("show");
        }
      });
    });
  }
// ====== NEW: Floating Navbar Logic ======
  
  // 1. Scroll Effect (Menambahkan class 'scrolled' saat turun)
  window.addEventListener('scroll', () => {
      const nav = document.querySelector('.floating-nav');
      if (nav) {
          if (window.scrollY > 50) {
              nav.classList.add('scrolled');
          } else {
              nav.classList.remove('scrolled');
          }
      }
  });

  // 2. Mobile Menu Toggle
  const mobileTrigger = document.getElementById('mobile-menu-trigger');
  const mobileClose = document.getElementById('mobile-menu-close');
  const mobileMenu = document.getElementById('mobile-menu');

  if (mobileTrigger && mobileMenu && mobileClose) {
      mobileTrigger.addEventListener('click', () => {
          mobileMenu.classList.add('active');
      });
      mobileClose.addEventListener('click', () => {
          mobileMenu.classList.remove('active');
      });
      // Tutup menu saat link di dalamnya diklik
      const mobileLinks = mobileMenu.querySelectorAll('a');
      mobileLinks.forEach(link => {
          link.addEventListener('click', () => {
              mobileMenu.classList.remove('active');
          });
      });
  }

  // 3. Active Link Highlighter (Intersection Observer)
  // Fungsinya agar link di navbar menyala otomatis saat section terlihat
  const sections = document.querySelectorAll("section[id], div[id='home']");
  const navLinks = document.querySelectorAll(".nav-link-item");

  if (sections.length > 0 && navLinks.length > 0) {
      const observerOptions = {
          root: null,
          rootMargin: '-30% 0px -70% 0px', // Area deteksi di tengah layar
          threshold: 0
      };

      const observer = new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
              if (entry.isIntersecting) {
                  // Hapus active dari semua link
                  navLinks.forEach(link => link.classList.remove('active'));
                  
                  // Cari link yang href-nya sesuai dengan id section ini
                  const id = entry.target.getAttribute('id');
                  const activeLink = document.querySelector(`.nav-link-item[href*="#${id}"]`);
                  
                  if (activeLink) {
                      activeLink.classList.add('active');
                  }
              }
          });
      }, observerOptions);

      sections.forEach((section) => {
          observer.observe(section);
      });
  }

})();