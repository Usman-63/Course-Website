export interface CourseLink {
  id: string;
  title: string;
  url: string;
  description?: string;
}

export const courseLinks: CourseLink[] = [
  {
    id: '1',
    title: 'Course Syllabus',
    url: 'https://docs.google.com/document/d/1K0Vc1PQ5d8LkKnx4OA7-wHeellGcEf5qZ5yUrOP2XvQ/edit?tab=t.0#heading=h.kmh80rsxsssq',
    description: 'Detailed breakdown of the 3-week curriculum.'
  },
  {
    id: '2',
    title: 'Register Now',
    url: 'https://docs.google.com/forms/d/e/1FAIpQLSe3WKayEEbdwZNox_w5rOFrPcCEhMvzHLcPHbz-SzYDSMWFcw/viewform',
    description: 'Sign up for the Gemini 3 Masterclass. Choose your program tier and payment method.'
  },
  {
    id: '3',
    title: 'WeChat',
    url: 'https://u.wechat.com/MMit10lJvgrnsWxLEIQIelY?s=2',
    description: 'Contact Andrew via WeChat for course support and questions.'
  },
  // Add more links here as needed
];
