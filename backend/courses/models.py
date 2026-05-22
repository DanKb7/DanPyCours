from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    """Категории курсов"""
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name='Описание')
    icon = models.CharField(max_length=50, blank=True, verbose_name='Иконка (emoji)')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_courses_count(self):
        return self.courses.filter(is_published=True).count()

class Course(models.Model):
    """Модель курса"""
    LEVEL_CHOICES = [
        ('beginner', 'Новичок'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Название курса')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(verbose_name='Описание')
    full_description = models.TextField(blank=True, verbose_name='Полное описание')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, 
                                 null=True, related_name='courses', verbose_name='Категория')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, 
                            default='beginner', verbose_name='Уровень')
    duration_months = models.IntegerField(default=3, verbose_name='Длительность (месяцев)')
    price = models.DecimalField(max_digits=10, decimal_places=2, 
                               default=0, verbose_name='Цена')
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, 
                                        blank=True, null=True, verbose_name='Цена со скидкой')
    image = models.ImageField(upload_to='courses/', blank=True, null=True, verbose_name='Изображение')
    students_count = models.IntegerField(default=0, verbose_name='Количество студентов')
    rating = models.DecimalField(max_digits=3, decimal_places=1, 
                                default=0, verbose_name='Рейтинг')
    reviews_count = models.IntegerField(default=0, verbose_name='Количество отзывов')
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price
    
    def get_level_badge_color(self):
        colors = {
            'beginner': 'green',
            'intermediate': 'yellow',
            'advanced': 'red',
        }
        return colors.get(self.level, 'gray')

class Module(models.Model):
    """Модуль курса"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, 
                               related_name='modules', verbose_name='Курс')
    title = models.CharField(max_length=200, verbose_name='Название модуля')
    description = models.TextField(blank=True, verbose_name='Описание')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    duration_weeks = models.IntegerField(default=2, verbose_name='Длительность (недель)')
    
    class Meta:
        verbose_name = 'Модуль'
        verbose_name_plural = 'Модули'
        ordering = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    """Урок в модуле"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, 
                               related_name='lessons', verbose_name='Модуль')
    title = models.CharField(max_length=200, verbose_name='Название урока')
    description = models.TextField(blank=True, verbose_name='Описание')
    video_url = models.URLField(blank=True, verbose_name='URL видео')
    content = models.TextField(blank=True, verbose_name='Содержание')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    duration_minutes = models.IntegerField(default=30, verbose_name='Длительность (минут)')
    is_free = models.BooleanField(default=False, verbose_name='Бесплатный урок')
    
    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['module', 'order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"

class Enrollment(models.Model):
    """Запись на курс"""
    STATUS_CHOICES = [
        ('enrolled', 'Записан'),
        ('in_progress', 'Проходит'),
        ('completed', 'Завершил'),
        ('cancelled', 'Отменил'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                             related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, 
                               related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, 
                              default='enrolled', verbose_name='Статус')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата записи')
    progress = models.IntegerField(default=0, verbose_name='Прогресс (%)')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')
    
    class Meta:
        verbose_name = 'Запись на курс'
        verbose_name_plural = 'Записи на курсы'
        unique_together = ['user', 'course']
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class Review(models.Model):
    """Отзыв о курсе"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                             related_name='reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, 
                               related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], 
                                verbose_name='Оценка')
    text = models.TextField(verbose_name='Текст отзыва')
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.rating})"