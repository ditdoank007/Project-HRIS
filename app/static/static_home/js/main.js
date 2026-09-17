(function ($) {
    "use strict";
    
    // Dropdown on mouse hover
    $(document).ready(function () {
        function toggleNavbarMethod() {
            if ($(window).width() > 992) {
                $('.navbar .dropdown').on('mouseover', function () {
                    $('.dropdown-toggle', this).trigger('click');
                }).on('mouseout', function () {
                    $('.dropdown-toggle', this).trigger('click').blur();
                });
            } else {
                $('.navbar .dropdown').off('mouseover').off('mouseout');
            }
        }
        toggleNavbarMethod();
        $(window).resize(toggleNavbarMethod);
    });


    // Date and time picker
    $('.date').datetimepicker({
        format: 'L'
    });
    $('.time').datetimepicker({
        format: 'LT'
    });
    
    
    // Back to top button
    $(window).scroll(function () {
        if ($(this).scrollTop() > 100) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });
    $('.back-to-top').click(function () {
        $('html, body').animate({scrollTop: 0}, 1500, 'easeInOutExpo');
        return false;
    });


    // Portfolio isotope and filter
    var portfolioIsotope = $('.portfolio-container').isotope({
        itemSelector: '.portfolio-item',
        layoutMode: 'fitRows'
    });
    $('#portfolio-flters li').on('click', function () {
        $("#portfolio-flters li").removeClass('active');
        $(this).addClass('active');

        portfolioIsotope.isotope({filter: $(this).data('filter')});
    });


    // Testimonials carousel
    $(".testimonial-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1000,
        items: 1,
        dots: false,
        loop: true,
    });
    
})(jQuery);


// Modal login Toggle lihat/sembunyikan password
document.getElementById('togglePassword').addEventListener('click', function () {
    const passwordInput = document.getElementById('inputPassword');
    const icon = document.getElementById('iconTogglePassword');
    const isPassword = passwordInput.getAttribute('type') === 'password';

    passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
    icon.classList.toggle('bi-eye-fill');
    icon.classList.toggle('bi-eye-slash-fill');
});

// Validasi dasar pakai Bootstrap validation classes
const formLogin = document.getElementById('formLogin');
formLogin.addEventListener('submit', function (e) {
    if (!formLogin.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
    }
    formLogin.classList.add('was-validated');

    // ganti baris di bawah dengan fetch() ke endpoint Flask, misal POST /login
    // Lihat catatan integrasi backend di bawah.
});

document.addEventListener('DOMContentLoaded', function () {
        const carouselElement = document.getElementById('header-carousel');
        
        // Inisialisasi Bootstrap Carousel dengan interval 15 detik
        const carousel = new bootstrap.Carousel(carouselElement, {
            interval: 2000,  // 15 detik
            ride: 'carousel',
            pause: false      // Jangan pause saat hover (opsional)
        });
    });



/* ============================================================
   HRIS HOME 2.0 - NAVBAR / HERO INTERACTION
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

    const navbar = document.querySelector('nav.navbar, .navbar');

    /* Navbar glass -> solid ketika scroll */
    if (navbar) {
        const updateNavbar = () => {
            navbar.classList.toggle('hris-navbar-scrolled', window.scrollY > 35);
        };

        updateNavbar();
        window.addEventListener('scroll', updateNavbar, { passive: true });
    }

    /* Hero scene animation */
    const hero = document.getElementById('header-carousel');

    if (hero) {
        const animateHero = () => {
            const active = hero.querySelector('.carousel-item.active');

            if (!active) return;

            active.classList.remove('hris-hero-scene');
            void active.offsetWidth;
            active.classList.add('hris-hero-scene');
        };

        animateHero();
        hero.addEventListener('slid.bs.carousel', animateHero);

        /* Subtle mouse movement / parallax */
        hero.addEventListener('mousemove', function (event) {
            const rect = hero.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
            const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;

            const activeImage = hero.querySelector(
                '.carousel-item.active img'
            );

            if (activeImage) {
                activeImage.style.transform =
                    `scale(1.035) translate(${x * 4}px, ${y * 3}px)`;
            }
        });

        hero.addEventListener('mouseleave', function () {
            const activeImage = hero.querySelector(
                '.carousel-item.active img'
            );

            if (activeImage) {
                activeImage.style.transform = 'scale(1.02)';
            }
        });
    }

    /* Dropdown modern interaction */
    document.querySelectorAll('.navbar .dropdown').forEach(function (dropdown) {

        dropdown.addEventListener('show.bs.dropdown', function () {
            dropdown.classList.add('hris-dropdown-opening');
        });

        dropdown.addEventListener('shown.bs.dropdown', function () {
            const menu = dropdown.querySelector('.dropdown-menu');

            if (!menu) return;

            menu.querySelectorAll('.dropdown-item').forEach(function (item, index) {
                item.style.setProperty(
                    '--dropdown-index',
                    index
                );
            });
        });

        dropdown.addEventListener('hidden.bs.dropdown', function () {
            dropdown.classList.remove('hris-dropdown-opening');
        });
    });

});

/* ============================================================
   HRIS HOME 2.0
   Cinematic Hero / Glass Navbar / Online Staff
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

    /* --------------------------------------------------------
       CAROUSEL — FORCE 2 SECOND INTERVAL
       -------------------------------------------------------- */
    const heroCarousel = document.getElementById('header-carousel');

    if (heroCarousel && window.bootstrap) {
        heroCarousel.setAttribute('data-bs-interval', '2000');

        const existingCarousel =
            bootstrap.Carousel.getInstance(heroCarousel);

        if (existingCarousel) {
            existingCarousel.dispose();
        }

        const modernCarousel = new bootstrap.Carousel(heroCarousel, {
            interval: 2000,
            ride: false,
            pause: false,
            touch: true,
            wrap: true
        });

        modernCarousel.cycle();

        /* Make sure a manual slide also continues autoplay */
        heroCarousel.addEventListener('slid.bs.carousel', function () {
            modernCarousel.cycle();
        });
    }

    /* --------------------------------------------------------
       NAVBAR GLASS STATE
       -------------------------------------------------------- */
    const navbar = document.querySelector('.navbar');

    if (navbar) {
        const updateNavbar = () => {
            navbar.classList.toggle(
                'hris-navbar-scrolled',
                window.scrollY > 60
            );
        };

        updateNavbar();

        window.addEventListener(
            'scroll',
            updateNavbar,
            { passive: true }
        );
    }

    /* --------------------------------------------------------
       HERO MOUSE PARALLAX
       -------------------------------------------------------- */
    if (heroCarousel) {

        heroCarousel.addEventListener('mousemove', function (event) {

            const rect = heroCarousel.getBoundingClientRect();

            const px =
                ((event.clientX - rect.left) / rect.width - 0.5) * 2;

            const py =
                ((event.clientY - rect.top) / rect.height - 0.5) * 2;

            const image =
                heroCarousel.querySelector(
                    '.carousel-item.active img'
                );

            if (image) {
                image.style.transform =
                    `scale(1.055) translate(${px * 4}px, ${py * 3}px)`;
            }
        });

        heroCarousel.addEventListener('mouseleave', function () {

            const image =
                heroCarousel.querySelector(
                    '.carousel-item.active img'
                );

            if (image) {
                image.style.transform = 'scale(1.035)';
            }
        });
    }

    /* --------------------------------------------------------
       DROPDOWN GLASS / SPARKLE
       -------------------------------------------------------- */
    document
        .querySelectorAll('.navbar .dropdown')
        .forEach(function (dropdown) {

            dropdown.addEventListener(
                'show.bs.dropdown',
                function () {
                    dropdown.classList.add(
                        'hris-dropdown-active'
                    );
                }
            );

            dropdown.addEventListener(
                'hidden.bs.dropdown',
                function () {
                    dropdown.classList.remove(
                        'hris-dropdown-active'
                    );
                }
            );
        });

    /* --------------------------------------------------------
       ONLINE STAFF CARD
       Mengambil angka online yang sudah tersedia di halaman.
       -------------------------------------------------------- */
    function findOnlineCount() {

        const elements =
            document.querySelectorAll('body *');

        for (const element of elements) {

            if (element.children.length > 0) {
                continue;
            }

            const text =
                (element.textContent || '').trim();

            const match =
                text.match(/online\s+(\d+)/i);

            if (match) {
                return match[1];
            }

            const reverseMatch =
                text.match(/(\d+)\s+online/i);

            if (reverseMatch) {
                return reverseMatch[1];
            }
        }

        return null;
    }

    function updateOnlineCard() {

        const count = findOnlineCount();

        const counter =
            document.getElementById('hrisHeroOnlineCount');

        if (counter && count !== null) {
            counter.textContent = count;
        }
    }

    updateOnlineCard();

    /*
     * Update berkala agar kartu mengikuti angka online
     * apabila data existing berubah.
     */
    setInterval(updateOnlineCard, 10000);

});
