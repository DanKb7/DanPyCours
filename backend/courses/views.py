from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.views.generic import ListView, DetailView
from .models import Course, Category, Enrollment, Review, UserLessonProgress, Module, Lesson

def index_view(request):
    """Главная страница"""
    courses = Course.objects.filter(is_published=True).select_related('category')[:6]
    categories = Category.objects.all()
    
    # Получаем курсы с наивысшим рейтингом
    top_courses = Course.objects.filter(
        is_published=True, 
        rating__gte=4.5
    ).order_by('-rating', '-students_count')[:3]
    
    context = {
        'courses': courses,
        'categories': categories,
        'top_courses': top_courses,
    }
    return render(request, 'index.html', context)

def error_404(request, exception):
    """Обработчик ошибки 404"""
    return render(request, '404.html', status=404)

def error_500(request):
    """Обработчик ошибки 500"""
    return render(request, '500.html', status=500)

class CourseListView(ListView):
    """Список всех курсов"""
    model = Course
    template_name = 'courses.html'
    context_object_name = 'courses'
    paginate_by = 9
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True).select_related('category')
        
        # Фильтрация по категории
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Фильтрация по уровню
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Поиск
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Сортировка
        sort_by = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_category'] = self.request.GET.get('category', '')
        context['current_level'] = self.request.GET.get('level', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context

class CourseDetailView(DetailView):
    """Детальная страница курса"""
    model = Course
    template_name = 'course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        # Получаем модули и уроки
        modules = course.modules.prefetch_related('lessons').all()
        
        # Получаем отзывы
        reviews = course.reviews.filter(
            is_published=True
        ).select_related('user').order_by('-created_at')[:5]
        
        # Проверяем, записан ли пользователь
        is_enrolled = False
        if self.request.user.is_authenticated:
            is_enrolled = Enrollment.objects.filter(
                user=self.request.user,
                course=course,
                status__in=['enrolled', 'in_progress']
            ).exists()
        
        # Похожие курсы
        related_courses = Course.objects.filter(
            category=course.category,
            is_published=True
        ).exclude(id=course.id)[:4]
        
        context.update({
            'modules': modules,
            'reviews': reviews,
            'is_enrolled': is_enrolled,
            'related_courses': related_courses,
        })
        return context

@login_required
def enroll_course(request, course_id):
    """Запись на курс"""
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Проверяем, не записан ли уже
    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={'status': 'enrolled'}
    )
    
    if created:
        messages.success(request, f'Вы успешно записались на курс "{course.title}"')
        course.students_count += 1
        course.save()
        # Перенаправляем на страницу обучения
        return redirect('courses:learning', slug=course.slug)
    else:
        messages.info(request, 'Вы уже записаны на этот курс')
        return redirect('courses:learning', slug=course.slug)

def about_view(request):
    """Страница о нас"""
    return render(request, 'about.html')

@login_required
def course_learning(request, slug):
    """Страница обучения - список уроков курса"""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    
    # Проверяем, записан ли пользователь
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    
    # Получаем все модули и уроки
    modules = course.modules.prefetch_related('lessons').all()
    
    # Получаем прогресс пользователя
    user_progress = UserLessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=course
    ).select_related('lesson')
    
    # Создаем словарь прогресса
    progress_dict = {p.lesson.id: p.status for p in user_progress}
    
    # Считаем общий прогресс
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = UserLessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=course,
        status='completed'
    ).count()
    
    progress_percentage = int((completed_lessons / total_lessons * 100)) if total_lessons > 0 else 0
    
    # Обновляем прогресс записи
    if enrollment.progress != progress_percentage:
        enrollment.progress = progress_percentage
        if progress_percentage == 100:
            enrollment.status = 'completed'
            enrollment.completed_at = timezone.now()
        elif progress_percentage > 0:
            enrollment.status = 'in_progress'
        enrollment.save()
    
    context = {
        'course': course,
        'modules': modules,
        'progress_dict': progress_dict,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'progress_percentage': progress_percentage,
        'enrollment': enrollment,
    }
    return render(request, 'course_learning.html', context)

@login_required
def lesson_detail(request, course_slug, lesson_id):
    """Страница конкретного урока"""
    course = get_object_or_404(Course, slug=course_slug, is_published=True)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    
    # Проверяем, записан ли пользователь
    get_object_or_404(Enrollment, user=request.user, course=course)
    
    # Получаем или создаем прогресс
    progress, created = UserLessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'status': 'in_progress'}
    )
    
    # Получаем предыдущий и следующий урок
    all_lessons = Lesson.objects.filter(module__course=course).order_by('module__order', 'order')
    lesson_list = list(all_lessons)
    current_index = lesson_list.index(lesson)
    
    prev_lesson = lesson_list[current_index - 1] if current_index > 0 else None
    next_lesson = lesson_list[current_index + 1] if current_index < len(lesson_list) - 1 else None
    
    # Получаем все модули для навигации
    modules = course.modules.prefetch_related('lessons').all()
    
    # Получаем прогресс по всем урокам
    user_progress = UserLessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=course
    ).select_related('lesson')
    
    progress_dict = {p.lesson.id: p.status for p in user_progress}
    
    context = {
        'course': course,
        'lesson': lesson,
        'progress': progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'modules': modules,
        'progress_dict': progress_dict,
    }
    return render(request, 'lesson_detail.html', context)

@login_required
def mark_lesson_complete(request, lesson_id):
    """Отметить урок как пройденный"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course
    
    # Проверяем, записан ли пользователь
    get_object_or_404(Enrollment, user=request.user, course=course)
    
    # Обновляем прогресс
    progress, created = UserLessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'status': 'completed', 'completed_at': timezone.now()}
    )
    
    if not created:
        progress.status = 'completed'
        progress.completed_at = timezone.now()
        progress.save()
    
    # Если запрос AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Урок пройден!'})
    
    # Иначе редирект
    messages.success(request, f'Урок "{lesson.title}" отмечен как пройденный!')
    return redirect('courses:lesson_detail', course_slug=course.slug, lesson_id=lesson.id)